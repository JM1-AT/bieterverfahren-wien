import io
import os
import json
import pyotp
import qrcode
import bcrypt
from datetime import datetime, timedelta
from flask import (Blueprint, render_template, request, redirect, url_for,
                   session, flash, current_app, Response, abort)
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User, Einladung, AuditLog
from i18n import t

auth_bp = Blueprint('auth', __name__)


# ─── Hilfsfunktionen ────────────────────────────────────────────────────────

def passwort_hashen(passwort: str) -> str:
    """Passwort mit bcrypt hashen."""
    return bcrypt.hashpw(passwort.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def passwort_pruefen(passwort: str, passwort_hash: str) -> bool:
    """Passwort gegen Hash prüfen."""
    return bcrypt.checkpw(passwort.encode('utf-8'), passwort_hash.encode('utf-8'))


def audit_log(aktion: str, details: dict = None, objekt_id: int = None):
    """Sicherheitsrelevante Aktion im Audit-Log speichern."""
    eintrag = AuditLog(
        user_id=current_user.id if current_user.is_authenticated else None,
        aktion=aktion,
        objekt_id=objekt_id,
        details=json.dumps(details or {}, ensure_ascii=False),
        ip_adresse=request.remote_addr,
        user_agent=request.user_agent.string[:500] if request.user_agent else None
    )
    db.session.add(eintrag)
    db.session.commit()


def audit_log_anonym(aktion: str, details: dict = None):
    """Audit-Log für nicht eingeloggte Aktionen (z.B. fehlgeschlagener Login)."""
    eintrag = AuditLog(
        user_id=None,
        aktion=aktion,
        details=json.dumps(details or {}, ensure_ascii=False),
        ip_adresse=request.remote_addr,
        user_agent=request.user_agent.string[:500] if request.user_agent else None
    )
    db.session.add(eintrag)
    db.session.commit()


# ─── Login / Logout ─────────────────────────────────────────────────────────

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login mit E-Mail und Passwort."""
    from app import limiter
    # Rate-Limiting: 5 Versuche pro Minute
    with current_app.test_request_context():
        pass  # Limiter wird via Decorator in app.py gesetzt

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        passwort = request.form.get('passwort', '')

        user = User.query.filter_by(email=email).first()

        # Benutzer nicht gefunden oder Passwort falsch
        if not user or not user.passwort_hash or not passwort_pruefen(passwort, user.passwort_hash):
            audit_log_anonym('login_fehlgeschlagen', {'email': email})
            flash(t('fehler_login'), 'error')
            return render_template('landing.html')

        # Status prüfen
        if user.status != 'aktiv':
            audit_log_anonym('login_inaktiv', {'email': email})
            flash('Ihr Konto ist noch nicht freigeschaltet.', 'error')
            return render_template('landing.html')

        # Admin braucht 2FA (nur wenn aktiviert)
        if user.rolle == 'admin' and user.totp_aktiviert:
            session['pending_user_id'] = user.id
            return redirect(url_for('auth.zwei_fa_verify'))

        # Admin ohne 2FA → direkt einloggen (2FA-Setup optional über Dashboard)

        # Einloggen und zur richtigen Seite weiterleiten
        login_user(user, remember=True)
        user.letzter_login = datetime.utcnow()
        db.session.commit()
        audit_log('login_erfolgreich', {'rolle': user.rolle})
        if user.rolle == 'admin':
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('bieter.dashboard'))

    return render_template('landing.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """Benutzer ausloggen."""
    audit_log('logout')
    logout_user()
    session.clear()
    return redirect(url_for('auth.login'))


# ─── 2FA für Admin ──────────────────────────────────────────────────────────

@auth_bp.route('/admin/2fa/setup', methods=['GET', 'POST'])
def zwei_fa_setup():
    """2FA einrichten – QR-Code anzeigen und TOTP-Secret speichern."""
    user_id = session.get('pending_user_id')
    if not user_id:
        return redirect(url_for('auth.login'))

    user = User.query.get(user_id)
    if not user or user.rolle != 'admin':
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        code = request.form.get('code', '').strip()
        totp = pyotp.TOTP(session.get('totp_secret_temp', ''))

        if totp.verify(code):
            # Secret in DB speichern und 2FA aktivieren
            user.totp_secret = session.pop('totp_secret_temp', '')
            user.totp_aktiviert = True
            db.session.commit()
            audit_log_anonym('2fa_eingerichtet', {'user_id': user.id})

            # Einloggen
            login_user(user, remember=True)
            user.letzter_login = datetime.utcnow()
            db.session.commit()
            return redirect(url_for('admin.dashboard'))
        else:
            flash(t('fehler_2fa'), 'error')

    # Neues TOTP-Secret generieren
    totp_secret = pyotp.random_base32()
    session['totp_secret_temp'] = totp_secret

    # QR-Code als Base64 generieren
    totp_uri = pyotp.totp.TOTP(totp_secret).provisioning_uri(
        name=user.email,
        issuer_name='Bieterverfahren Wien'
    )
    qr = qrcode.make(totp_uri)
    buf = io.BytesIO()
    qr.save(buf, format='PNG')
    import base64
    qr_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')

    return render_template('admin/2fa_setup.html', qr_base64=qr_base64, totp_secret=totp_secret)


@auth_bp.route('/admin/2fa/verify', methods=['GET', 'POST'])
def zwei_fa_verify():
    """2FA-Code bei jedem Admin-Login prüfen."""
    user_id = session.get('pending_user_id')
    if not user_id:
        return redirect(url_for('auth.login'))

    user = User.query.get(user_id)
    if not user or user.rolle != 'admin':
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        code = request.form.get('code', '').strip()
        totp = pyotp.TOTP(user.totp_secret)

        if totp.verify(code):
            session.pop('pending_user_id', None)
            login_user(user, remember=True)
            user.letzter_login = datetime.utcnow()
            db.session.commit()
            audit_log('2fa_erfolgreich')
            return redirect(url_for('admin.dashboard'))
        else:
            audit_log_anonym('2fa_fehlgeschlagen', {'user_id': user_id})
            flash(t('fehler_2fa'), 'error')

    return render_template('admin/2fa_verify.html')


# ─── Einladungs-Flow ────────────────────────────────────────────────────────

@auth_bp.route('/einladung/<token>', methods=['GET', 'POST'])
def einladung(token):
    """Einladungslink – Passwort setzen und Konto aktivieren."""
    einladung_obj = Einladung.query.filter_by(token=token).first()

    if not einladung_obj or not einladung_obj.ist_gueltig():
        flash(t('einladung_abgelaufen'), 'error')
        return render_template('einladung.html', ungueltig=True)

    if request.method == 'POST':
        passwort = request.form.get('passwort', '')
        passwort2 = request.form.get('passwort2', '')

        if len(passwort) < 8:
            flash('Das Passwort muss mindestens 8 Zeichen lang sein.', 'error')
            return render_template('einladung.html', token=token)

        if passwort != passwort2:
            flash('Die Passwörter stimmen nicht überein.', 'error')
            return render_template('einladung.html', token=token)

        # Benutzer aktivieren oder neu erstellen
        user = User.query.filter_by(email=einladung_obj.email).first()
        if not user:
            user = User(
                email=einladung_obj.email,
                name=einladung_obj.name or einladung_obj.email,
                rolle='bieter',
                status='aktiv'
            )
            db.session.add(user)

        user.passwort_hash = passwort_hashen(passwort)
        user.status = 'aktiv'
        einladung_obj.verwendet = True
        db.session.commit()

        audit_log_anonym('konto_aktiviert', {'email': user.email})
        flash('Ihr Konto wurde aktiviert. Sie können sich jetzt einloggen.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('einladung.html', token=token, einladung=einladung_obj)


# ─── Anfrage-Formular (öffentlich) ──────────────────────────────────────────

@auth_bp.route('/anfrage', methods=['GET', 'POST'])
def anfrage():
    """Öffentliches Formular – Zugang anfragen."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        firma = request.form.get('firma', '').strip()
        begruendung = request.form.get('begruendung', '').strip()

        if not name or not email:
            flash('Bitte füllen Sie alle Pflichtfelder aus.', 'error')
            return render_template('anfrage.html')

        # Bereits vorhanden?
        if User.query.filter_by(email=email).first():
            flash('Diese E-Mail-Adresse ist bereits registriert.', 'error')
            return render_template('anfrage.html')

        # Neuen Nutzer mit Status "ausstehend" anlegen
        user = User(
            email=email,
            name=name,
            firma=firma,
            rolle='bieter',
            status='ausstehend'
        )
        db.session.add(user)

        # Anfrage im Audit-Log speichern
        eintrag = AuditLog(
            aktion='anfrage_eingegangen',
            details=json.dumps({
                'name': name, 'email': email,
                'firma': firma, 'begruendung': begruendung
            }, ensure_ascii=False),
            ip_adresse=request.remote_addr,
            user_agent=request.user_agent.string[:500] if request.user_agent else None
        )
        db.session.add(eintrag)
        db.session.commit()

        flash(t('anfrage_success'), 'success')
        return redirect(url_for('auth.login'))

    return render_template('anfrage.html')


# ─── NDA-Dokument PDF ────────────────────────────────────────────────────────

def nda_pdf_pfad() -> str:
    """Pfad zur hochgeladenen NDA-PDF-Datei."""
    return os.path.join(current_app.config['UPLOAD_FOLDER'], 'nda', 'nda_dokument.pdf')


def nda_pdf_vorhanden() -> bool:
    """True wenn ein NDA-PDF hochgeladen wurde."""
    try:
        return os.path.exists(nda_pdf_pfad())
    except Exception:
        return False


@auth_bp.route('/nda-dokument')
@login_required
def nda_dokument():
    """NDA-PDF streamen – für alle eingeloggten Nutzer (Bieter + Admin)."""
    pfad = nda_pdf_pfad()
    if not os.path.exists(pfad):
        abort(404)
    with open(pfad, 'rb') as f:
        inhalt = f.read()
    return Response(inhalt, mimetype='application/pdf',
                    headers={'Content-Disposition': 'inline; filename=NDA_Bieterbedingungen.pdf'})


# ─── Sprachumschalter ───────────────────────────────────────────────────────

@auth_bp.route('/sprache/<lang>')
def sprache(lang):
    """Sprache wechseln (DE/EN)."""
    if lang in ('de', 'en'):
        session['lang'] = lang
    return redirect(request.referrer or url_for('auth.login'))
