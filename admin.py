import io
import uuid
import os
from datetime import datetime, timedelta
from functools import wraps
from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, send_file, Response)
from flask_login import login_required, current_user
from models import db, User, Objekt, Dokument, Gebot, ObjektZugang, Zustimmung, AuditLog, Einladung, ObjektFoto, SliderBild
from security import verschluesseln, sicherer_dateiname, erlaubte_datei, upload_pfad, foto_pfad, objekt_nda_pfad, objekt_nda_vorhanden
from mail import mail_einladung, mail_anfrage_bestaetigt, mail_anfrage_abgelehnt
from auth import audit_log

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


# ─── Zugriffsschutz ─────────────────────────────────────────────────────────

def admin_required(f):
    """Decorator: Nur für eingeloggte Admins."""
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if current_user.rolle != 'admin':
            flash('Kein Zugang.', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


def _einladungslink_erstellen(email: str, name: str, admin_user: User) -> str:
    """Einladungstoken generieren und Link zurückgeben."""
    token = str(uuid.uuid4())
    einladung = Einladung(
        email=email,
        name=name,
        token=token,
        gueltig_bis=datetime.utcnow() + timedelta(hours=72),
        erstellt_von=admin_user.id
    )
    db.session.add(einladung)
    db.session.commit()
    return url_for('auth.einladung', token=token, _external=True)


# ─── Dashboard ──────────────────────────────────────────────────────────────

@admin_bp.route('/')
@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    """Admin-Dashboard: Metriken, offene Anfragen, aktive Verfahren."""
    # Metriken
    aktive_objekte = Objekt.query.filter_by(aktiv=True).count()
    aktive_bieter = User.query.filter_by(rolle='bieter', status='aktiv').count()
    offene_anfragen = User.query.filter_by(rolle='bieter', status='ausstehend').count()

    # NDA-Ratio: Bieter mit mindestens einer Bestätigung / alle aktiven Bieter
    bieter_mit_nda = db.session.query(Zustimmung.user_id).distinct().count()
    nda_ratio = f'{bieter_mit_nda}/{aktive_bieter}' if aktive_bieter else '0/0'

    # Offene Anfragen (Nutzer-Objekte)
    anfragen = User.query.filter_by(rolle='bieter', status='ausstehend').order_by(User.erstellt_am.desc()).limit(10).all()

    # Aktive Verfahren
    objekte = Objekt.query.order_by(Objekt.ende.asc()).all()

    # NDA-Übersicht für das erste aktive Objekt
    erstes_aktives = Objekt.query.filter_by(aktiv=True).first()
    nda_uebersicht = []
    if erstes_aktives:
        for zugang in erstes_aktives.zugaenge:
            zustimmung = Zustimmung.query.filter_by(
                user_id=zugang.user_id,
                objekt_id=erstes_aktives.id
            ).first()
            nda_uebersicht.append({
                'user': zugang.user,
                'zustimmung': zustimmung
            })

    slider_bilder = SliderBild.query.order_by(SliderBild.reihenfolge).all()

    return render_template('admin/dashboard.html',
                           aktive_objekte=aktive_objekte,
                           aktive_bieter=aktive_bieter,
                           offene_anfragen=offene_anfragen,
                           nda_ratio=nda_ratio,
                           anfragen=anfragen,
                           objekte=objekte,
                           nda_uebersicht=nda_uebersicht,
                           erstes_aktives=erstes_aktives,
                           slider_bilder=slider_bilder)


# ─── Objekte ────────────────────────────────────────────────────────────────

@admin_bp.route('/objekte')
@admin_required
def objekte():
    """Liste aller Objekte."""
    alle_objekte = Objekt.query.order_by(Objekt.erstellt_am.desc()).all()
    return render_template('admin/objekte.html', objekte=alle_objekte)


@admin_bp.route('/objekte/neu', methods=['GET', 'POST'])
@admin_required
def objekt_neu():
    """Neues Objekt anlegen."""
    if request.method == 'POST':
        # Datumsfelder parsen
        def parse_dt(field):
            val = request.form.get(field, '').strip()
            if not val:
                return None
            try:
                return datetime.strptime(val, '%Y-%m-%dT%H:%M')
            except ValueError:
                try:
                    return datetime.strptime(val, '%Y-%m-%d')
                except ValueError:
                    return None

        objekt = Objekt(
            titel=request.form.get('titel', '').strip(),
            objektnummer=request.form.get('objektnummer', '').strip() or None,
            geschaeftsbeziehung=request.form.get('geschaeftsbeziehung', 'B2C'),
            flaeche_m2=float(request.form.get('flaeche_m2') or 0) or None,
            strasse=request.form.get('strasse', '').strip(),
            plz=request.form.get('plz', '').strip(),
            ort=request.form.get('ort', '').strip(),
            land=request.form.get('land', 'Österreich').strip(),
            beschreibung=request.form.get('beschreibung', '').strip(),
            link_detailbeschreibung=request.form.get('link_detailbeschreibung', '').strip() or None,
            link_3d_rundgang=request.form.get('link_3d_rundgang', '').strip() or None,
            beginn=parse_dt('beginn'),
            ende=parse_dt('ende'),
            startpreis=float(request.form.get('startpreis', 0)),
            zielpreis=float(request.form.get('zielpreis') or 0) or None,
            sofortkauf_aktiv='sofortkauf_aktiv' in request.form,
            sofortkauf_preis=float(request.form.get('sofortkauf_preis') or 0) or None,
            maklerprovision=float(request.form.get('maklerprovision', 3.0)),
            notarkosten=float(request.form.get('notarkosten', 1.5)),
            grunderwerbssteuer=float(request.form.get('grunderwerbssteuer', 3.5)),
            grundbuch_gebuehr=float(request.form.get('grundbuch_gebuehr', 1.1)),
            gew_nebenkosten_ausblenden='gew_nebenkosten_ausblenden' in request.form,
            gb_nebenkosten_ausblenden='gb_nebenkosten_ausblenden' in request.form,
            binding_bestaetigung_ausblenden='binding_bestaetigung_ausblenden' in request.form,
            angebotsliste_ausblenden='angebotsliste_ausblenden' in request.form,
            zusatzvereinbarungen=request.form.get('zusatzvereinbarungen', '').strip() or None,
            erstellt_von=current_user.id,
            aktiv=True
        )
        db.session.add(objekt)
        db.session.commit()

        # Dokumente hochladen
        _dokumente_hochladen(objekt.id, request.files.getlist('dokumente'))

        audit_log('objekt_erstellt', {'titel': objekt.titel}, objekt_id=objekt.id)
        flash(f'Objekt „{objekt.titel}" wurde angelegt.', 'success')
        return redirect(url_for('admin.objekt_detail', objekt_id=objekt.id))

    return render_template('admin/objekt_neu.html')


@admin_bp.route('/objekte/<int:objekt_id>')
@admin_required
def objekt_detail(objekt_id):
    """Objektdetail für Admin: Gebote, NDA-Status, Bieter, Dokumente."""
    objekt = Objekt.query.get_or_404(objekt_id)

    # Alle Gebote (mit Namen – nur Admin sieht das)
    gebote = Gebot.query.filter_by(objekt_id=objekt_id).order_by(Gebot.betrag.desc()).all()

    # NDA-Bestätigungen pro Bieter
    nda_uebersicht = []
    for zugang in objekt.zugaenge:
        zustimmung = Zustimmung.query.filter_by(
            user_id=zugang.user_id,
            objekt_id=objekt_id
        ).first()
        nda_uebersicht.append({'user': zugang.user, 'zustimmung': zustimmung})

    # Alle aktiven Bieter (für Einladungs-Dropdown)
    alle_bieter = User.query.filter_by(rolle='bieter', status='aktiv').all()
    eingeladene_ids = {z.user_id for z in objekt.zugaenge}

    fotos = ObjektFoto.query.filter_by(objekt_id=objekt_id).order_by(ObjektFoto.reihenfolge).all()
    nda_pdf = objekt_nda_vorhanden(objekt_id)

    return render_template('admin/objekt_detail.html',
                           objekt=objekt,
                           gebote=gebote,
                           nda_uebersicht=nda_uebersicht,
                           alle_bieter=alle_bieter,
                           eingeladene_ids=eingeladene_ids,
                           fotos=fotos,
                           nda_pdf=nda_pdf)


@admin_bp.route('/objekte/<int:objekt_id>/bieter-hinzufuegen', methods=['POST'])
@admin_required
def bieter_hinzufuegen(objekt_id):
    """Bieter zu einem Objekt hinzufügen."""
    Objekt.query.get_or_404(objekt_id)
    user_id = request.form.get('user_id', type=int)

    if not user_id:
        flash('Kein Bieter ausgewählt.', 'error')
        return redirect(url_for('admin.objekt_detail', objekt_id=objekt_id))

    # Bereits vorhanden?
    if ObjektZugang.query.filter_by(objekt_id=objekt_id, user_id=user_id).first():
        flash('Bieter hat bereits Zugang.', 'error')
        return redirect(url_for('admin.objekt_detail', objekt_id=objekt_id))

    zugang = ObjektZugang(objekt_id=objekt_id, user_id=user_id)
    db.session.add(zugang)
    db.session.commit()
    audit_log('bieter_hinzugefuegt', {'user_id': user_id}, objekt_id=objekt_id)
    flash('Bieter wurde hinzugefügt.', 'success')
    return redirect(url_for('admin.objekt_detail', objekt_id=objekt_id))


@admin_bp.route('/objekte/<int:objekt_id>/bieter-entfernen/<int:user_id>', methods=['POST'])
@admin_required
def bieter_entfernen(objekt_id, user_id):
    """Bieter von einem Objekt entfernen."""
    zugang = ObjektZugang.query.filter_by(objekt_id=objekt_id, user_id=user_id).first_or_404()
    db.session.delete(zugang)
    db.session.commit()
    audit_log('bieter_entfernt', {'user_id': user_id}, objekt_id=objekt_id)
    flash('Bieter wurde entfernt.', 'success')
    return redirect(url_for('admin.objekt_detail', objekt_id=objekt_id))


@admin_bp.route('/objekte/<int:objekt_id>/nda-upload', methods=['POST'])
@admin_required
def objekt_nda_upload(objekt_id):
    """NDA-PDF für dieses Objekt hochladen."""
    Objekt.query.get_or_404(objekt_id)
    datei = request.files.get('nda_pdf')
    if not datei or not datei.filename.lower().endswith('.pdf'):
        flash('Bitte eine PDF-Datei hochladen.', 'error')
        return redirect(url_for('admin.objekt_detail', objekt_id=objekt_id))
    datei.save(objekt_nda_pfad(objekt_id))
    audit_log('objekt_nda_hochgeladen', {'datei': datei.filename}, objekt_id=objekt_id)
    flash('NDA/Bieterbedingungen für dieses Objekt hochgeladen.', 'success')
    return redirect(url_for('admin.objekt_detail', objekt_id=objekt_id))


@admin_bp.route('/objekte/<int:objekt_id>/nda-loeschen', methods=['POST'])
@admin_required
def objekt_nda_loeschen(objekt_id):
    """NDA-PDF für dieses Objekt löschen."""
    pfad = objekt_nda_pfad(objekt_id)
    if os.path.exists(pfad):
        os.remove(pfad)
        audit_log('objekt_nda_geloescht', {}, objekt_id=objekt_id)
        flash('NDA-Dokument gelöscht. Platzhaltertext wird wieder verwendet.', 'success')
    return redirect(url_for('admin.objekt_detail', objekt_id=objekt_id))


@admin_bp.route('/objekte/<int:objekt_id>/nda-vorschau')
@admin_required
def objekt_nda_vorschau(objekt_id):
    """NDA-PDF für Admin streamen (Vorschau)."""
    import mimetypes
    pfad = objekt_nda_pfad(objekt_id)
    if not os.path.exists(pfad):
        flash('Kein NDA-Dokument vorhanden.', 'error')
        return redirect(url_for('admin.objekt_detail', objekt_id=objekt_id))
    with open(pfad, 'rb') as f:
        inhalt = f.read()
    return Response(inhalt, mimetype='application/pdf',
                    headers={'Content-Disposition': 'inline; filename=NDA_Objekt.pdf'})


@admin_bp.route('/objekte/<int:objekt_id>/dokument-upload', methods=['POST'])
@admin_required
def dokument_upload(objekt_id):
    """Dokumente zu einem Objekt hochladen."""
    Objekt.query.get_or_404(objekt_id)
    _dokumente_hochladen(objekt_id, request.files.getlist('dokumente'))
    flash('Dokumente wurden hochgeladen.', 'success')
    return redirect(url_for('admin.objekt_detail', objekt_id=objekt_id))


@admin_bp.route('/objekte/<int:objekt_id>/dokument-loeschen/<int:dok_id>', methods=['POST'])
@admin_required
def dokument_loeschen(objekt_id, dok_id):
    """Dokument löschen."""
    dok = Dokument.query.filter_by(id=dok_id, objekt_id=objekt_id).first_or_404()
    pfad = os.path.join(upload_pfad(objekt_id), dok.gespeicherter_name)
    if os.path.exists(pfad):
        os.remove(pfad)
    db.session.delete(dok)
    db.session.commit()
    audit_log('dokument_geloescht', {'datei': dok.original_name}, objekt_id=objekt_id)
    flash('Dokument wurde gelöscht.', 'success')
    return redirect(url_for('admin.objekt_detail', objekt_id=objekt_id))


@admin_bp.route('/objekte/<int:objekt_id>/foto-upload', methods=['POST'])
@admin_required
def foto_upload(objekt_id):
    """Fotos zu einem Objekt hochladen (unverschlüsselt, für Slider)."""
    Objekt.query.get_or_404(objekt_id)
    dateien = request.files.getlist('fotos')
    erlaubte_foto_endungen = {'jpg', 'jpeg', 'png', 'webp'}
    hochgeladen = 0

    for datei in dateien:
        if not datei or not datei.filename:
            continue
        endung = datei.filename.rsplit('.', 1)[-1].lower() if '.' in datei.filename else ''
        if endung not in erlaubte_foto_endungen:
            flash(f'Datei „{datei.filename}" ist kein gültiges Foto (jpg/jpeg/png/webp).', 'error')
            continue

        uuid_name = sicherer_dateiname(datei.filename)
        pfad = os.path.join(foto_pfad(objekt_id), uuid_name)
        datei.save(pfad)

        # Reihenfolge: höchste bisherige + 10
        max_reihenfolge = db.session.query(db.func.max(ObjektFoto.reihenfolge)).filter_by(
            objekt_id=objekt_id
        ).scalar() or 0

        foto = ObjektFoto(
            objekt_id=objekt_id,
            gespeicherter_name=uuid_name,
            original_name=datei.filename,
            reihenfolge=max_reihenfolge + 10
        )
        db.session.add(foto)
        hochgeladen += 1

    db.session.commit()
    if hochgeladen:
        audit_log('fotos_hochgeladen', {'anzahl': hochgeladen}, objekt_id=objekt_id)
        flash(f'{hochgeladen} Foto(s) hochgeladen.', 'success')
    return redirect(url_for('admin.objekt_detail', objekt_id=objekt_id))


@admin_bp.route('/objekte/<int:objekt_id>/foto-loeschen/<int:foto_id>', methods=['POST'])
@admin_required
def foto_loeschen(objekt_id, foto_id):
    """Foto löschen."""
    foto = ObjektFoto.query.filter_by(id=foto_id, objekt_id=objekt_id).first_or_404()
    pfad = os.path.join(foto_pfad(objekt_id), foto.gespeicherter_name)
    if os.path.exists(pfad):
        os.remove(pfad)
    db.session.delete(foto)
    db.session.commit()
    audit_log('foto_geloescht', {'datei': foto.original_name}, objekt_id=objekt_id)
    flash('Foto wurde gelöscht.', 'success')
    return redirect(url_for('admin.objekt_detail', objekt_id=objekt_id))


@admin_bp.route('/objekte/<int:objekt_id>/fotos/<gespeicherter_name>')
@admin_required
def foto_ansehen(objekt_id, gespeicherter_name):
    """Foto direkt streamen (für Admin-Vorschau im Slider)."""
    import mimetypes
    pfad = os.path.join(foto_pfad(objekt_id), gespeicherter_name)
    if not os.path.exists(pfad):
        from flask import abort
        abort(404)
    mime = mimetypes.guess_type(pfad)[0] or 'image/jpeg'
    with open(pfad, 'rb') as f:
        inhalt = f.read()
    from flask import Response
    return Response(inhalt, mimetype=mime)


def _dokumente_hochladen(objekt_id: int, dateien):
    """Mehrere Dateien verschlüsselt speichern."""
    for datei in dateien:
        if not datei or not datei.filename:
            continue
        if not erlaubte_datei(datei.filename):
            flash(f'Datei „{datei.filename}" ist nicht erlaubt.', 'error')
            continue

        # Datei lesen und verschlüsseln
        inhalt = datei.read()
        groesse_kb = len(inhalt) // 1024
        verschluesselt_inhalt = verschluesseln(inhalt)

        # UUID-Dateiname
        uuid_name = sicherer_dateiname(datei.filename)
        pfad = os.path.join(upload_pfad(objekt_id), uuid_name)

        with open(pfad, 'wb') as f:
            f.write(verschluesselt_inhalt)

        endung = datei.filename.rsplit('.', 1)[1].lower() if '.' in datei.filename else ''

        dok = Dokument(
            objekt_id=objekt_id,
            original_name=datei.filename,
            gespeicherter_name=uuid_name,
            dateityp=endung,
            groesse_kb=groesse_kb,
            verschluesselt=True,
            hochgeladen_von=current_user.id
        )
        db.session.add(dok)

    db.session.commit()


# ─── Admin: Dokument-Download (auch für Admin) ───────────────────────────────

@admin_bp.route('/dokument/<int:dok_id>')
@admin_required
def dokument_download(dok_id):
    """Verschlüsseltes Dokument entschlüsseln und streamen."""
    from security import entschluesseln
    dok = Dokument.query.get_or_404(dok_id)
    pfad = os.path.join(upload_pfad(dok.objekt_id), dok.gespeicherter_name)

    if not os.path.exists(pfad):
        flash('Dokument nicht gefunden.', 'error')
        return redirect(url_for('admin.objekt_detail', objekt_id=dok.objekt_id))

    with open(pfad, 'rb') as f:
        verschluesselt_inhalt = f.read()

    inhalt = entschluesseln(verschluesselt_inhalt)
    audit_log('dokument_download', {'datei': dok.original_name}, objekt_id=dok.objekt_id)

    return send_file(
        io.BytesIO(inhalt),
        download_name=dok.original_name,
        as_attachment=True
    )


# ─── Anfragen ────────────────────────────────────────────────────────────────

@admin_bp.route('/anfragen')
@admin_required
def anfragen():
    """Alle offenen Zugriffsanfragen."""
    offene = User.query.filter_by(rolle='bieter', status='ausstehend').order_by(User.erstellt_am.desc()).all()
    return render_template('admin/anfragen.html', anfragen=offene)


@admin_bp.route('/anfragen/<int:user_id>/bestaetigen', methods=['POST'])
@admin_required
def anfrage_bestaetigen(user_id):
    """Zugriffsanfrage bestätigen und Einladungslink senden."""
    user = User.query.get_or_404(user_id)
    link = _einladungslink_erstellen(user.email, user.name, current_user)
    mail_anfrage_bestaetigt(user.email, user.name, link)
    audit_log('anfrage_bestaetigt', {'user_id': user_id, 'email': user.email})
    flash(f'Einladungslink an {user.email} gesendet (siehe Console).', 'success')
    return redirect(url_for('admin.anfragen'))


@admin_bp.route('/anfragen/<int:user_id>/ablehnen', methods=['POST'])
@admin_required
def anfrage_ablehnen(user_id):
    """Zugriffsanfrage ablehnen."""
    user = User.query.get_or_404(user_id)
    user.status = 'abgelehnt'
    db.session.commit()
    mail_anfrage_abgelehnt(user.email, user.name)
    audit_log('anfrage_abgelehnt', {'user_id': user_id, 'email': user.email})
    flash(f'Anfrage von {user.name} wurde abgelehnt.', 'success')
    return redirect(url_for('admin.anfragen'))


# ─── Nutzer ──────────────────────────────────────────────────────────────────

@admin_bp.route('/nutzer')
@admin_required
def nutzer():
    """Alle Nutzer mit Status und NDA-Übersicht."""
    alle_nutzer = User.query.order_by(User.erstellt_am.desc()).all()

    # NDA-Statistik pro Nutzer
    nutzer_stats = []
    for user in alle_nutzer:
        nda_count = Zustimmung.query.filter_by(user_id=user.id).count()
        zugaenge_count = ObjektZugang.query.filter_by(user_id=user.id).count()
        nutzer_stats.append({
            'user': user,
            'nda_count': nda_count,
            'zugaenge_count': zugaenge_count
        })

    return render_template('admin/nutzer.html', nutzer_stats=nutzer_stats)


@admin_bp.route('/nutzer/einladen', methods=['POST'])
@admin_required
def nutzer_einladen():
    """Bieter manuell einladen."""
    email = request.form.get('email', '').strip().lower()
    name = request.form.get('name', '').strip()

    if not email or not name:
        flash('E-Mail und Name sind erforderlich.', 'error')
        return redirect(url_for('admin.nutzer'))

    # Falls noch nicht vorhanden – Nutzer anlegen
    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(email=email, name=name, rolle='bieter', status='ausstehend')
        db.session.add(user)
        db.session.commit()

    link = _einladungslink_erstellen(email, name, current_user)
    mail_einladung(email, name, link)
    audit_log('einladung_gesendet', {'email': email})
    flash(f'Einladungslink an {email} gesendet (siehe Console).', 'success')
    return redirect(url_for('admin.nutzer'))


@admin_bp.route('/nutzer/xlsx-import', methods=['POST'])
@admin_required
def nutzer_xlsx_import():
    """Bieter per XLSX-Datei massenimportieren (Spalten: email, name, firma)."""
    import openpyxl

    datei = request.files.get('xlsx_datei')
    if not datei or not datei.filename.lower().endswith('.xlsx'):
        flash('Bitte eine .xlsx-Datei hochladen.', 'error')
        return redirect(url_for('admin.nutzer'))

    try:
        wb = openpyxl.load_workbook(datei, read_only=True, data_only=True)
        ws = wb.active
    except Exception:
        flash('Die Datei konnte nicht gelesen werden. Bitte gültiges XLSX hochladen.', 'error')
        return redirect(url_for('admin.nutzer'))

    # Erste Zeile als Header erkennen
    zeilen = list(ws.iter_rows(values_only=True))
    if not zeilen:
        flash('Die XLSX-Datei ist leer.', 'error')
        return redirect(url_for('admin.nutzer'))

    # Spaltennamen aus erster Zeile (case-insensitive)
    header = [str(h).strip().lower() if h else '' for h in zeilen[0]]

    def spalte(name):
        return header.index(name) if name in header else None

    idx_email = spalte('email')
    idx_name = spalte('name')
    idx_firma = spalte('firma')

    if idx_email is None or idx_name is None:
        flash('Die XLSX muss mindestens die Spalten „email" und „name" enthalten.', 'error')
        return redirect(url_for('admin.nutzer'))

    erstellt = 0
    uebersprungen = 0

    for zeile in zeilen[1:]:
        email = str(zeile[idx_email]).strip().lower() if zeile[idx_email] else ''
        name = str(zeile[idx_name]).strip() if zeile[idx_name] else ''
        firma = str(zeile[idx_firma]).strip() if idx_firma is not None and zeile[idx_firma] else ''

        if not email or not name or '@' not in email:
            uebersprungen += 1
            continue

        # Bereits vorhanden?
        if User.query.filter_by(email=email).first():
            uebersprungen += 1
            continue

        user = User(email=email, name=name, firma=firma or None, rolle='bieter', status='ausstehend')
        db.session.add(user)
        db.session.flush()  # ID für Einladung generieren

        link = _einladungslink_erstellen(email, name, current_user)
        mail_einladung(email, name, link)
        erstellt += 1

    db.session.commit()
    audit_log('xlsx_import', {'erstellt': erstellt, 'uebersprungen': uebersprungen})
    flash(f'Import abgeschlossen: {erstellt} Bieter angelegt, {uebersprungen} übersprungen.', 'success')
    return redirect(url_for('admin.nutzer'))


# ─── Einstellungen (NDA-Dokument) ────────────────────────────────────────────

@admin_bp.route('/einstellungen', methods=['GET', 'POST'])
@admin_required
def einstellungen():
    """Einstellungsseite: NDA/Bieterbedingungen-PDF hochladen."""
    from auth import nda_pdf_pfad, nda_pdf_vorhanden

    if request.method == 'POST':
        datei = request.files.get('nda_pdf')
        if not datei or not datei.filename.lower().endswith('.pdf'):
            flash('Bitte eine PDF-Datei hochladen.', 'error')
            return redirect(url_for('admin.einstellungen'))

        # Verzeichnis anlegen
        pfad = nda_pdf_pfad()
        os.makedirs(os.path.dirname(pfad), exist_ok=True)
        datei.save(pfad)

        audit_log('nda_dokument_hochgeladen', {'datei': datei.filename})
        flash('NDA/Bieterbedingungen wurde erfolgreich hochgeladen.', 'success')
        return redirect(url_for('admin.einstellungen'))

    pdf_vorhanden = nda_pdf_vorhanden()
    return render_template('admin/einstellungen.html', pdf_vorhanden=pdf_vorhanden)


@admin_bp.route('/einstellungen/nda-loeschen', methods=['POST'])
@admin_required
def nda_loeschen():
    """NDA-PDF löschen (Fallback auf Platzhaltertext)."""
    from auth import nda_pdf_pfad
    pfad = nda_pdf_pfad()
    if os.path.exists(pfad):
        os.remove(pfad)
        audit_log('nda_dokument_geloescht')
        flash('NDA-Dokument wurde gelöscht. Platzhaltertext wird wieder verwendet.', 'success')
    return redirect(url_for('admin.einstellungen'))


# ─── Slider-Bilder (plattformweit) ───────────────────────────────────────────

def _slider_pfad() -> str:
    """Upload-Verzeichnis für Slider-Bilder."""
    import os as _os
    pfad = _os.path.join(_os.path.dirname(__file__), 'uploads', 'slider')
    _os.makedirs(pfad, exist_ok=True)
    return pfad


@admin_bp.route('/slider/upload', methods=['POST'])
@admin_required
def slider_upload():
    """Bilder für den Dashboard-Slider hochladen."""
    erlaubte = {'jpg', 'jpeg', 'png', 'webp'}
    dateien = request.files.getlist('slider_bilder')
    hochgeladen = 0
    for datei in dateien:
        if not datei or not datei.filename:
            continue
        endung = datei.filename.rsplit('.', 1)[-1].lower() if '.' in datei.filename else ''
        if endung not in erlaubte:
            flash(f'„{datei.filename}" ist kein gültiges Bild (jpg/png/webp).', 'error')
            continue
        uuid_name = sicherer_dateiname(datei.filename)
        datei.save(os.path.join(_slider_pfad(), uuid_name))
        max_r = db.session.query(db.func.max(SliderBild.reihenfolge)).scalar() or 0
        db.session.add(SliderBild(
            gespeicherter_name=uuid_name,
            original_name=datei.filename,
            reihenfolge=max_r + 10
        ))
        hochgeladen += 1
    db.session.commit()
    if hochgeladen:
        audit_log('slider_bild_hochgeladen', {'anzahl': hochgeladen})
        flash(f'{hochgeladen} Bild(er) hochgeladen.', 'success')
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/slider/loeschen/<int:bild_id>', methods=['POST'])
@admin_required
def slider_loeschen(bild_id):
    """Slider-Bild löschen."""
    bild = SliderBild.query.get_or_404(bild_id)
    pfad = os.path.join(_slider_pfad(), bild.gespeicherter_name)
    if os.path.exists(pfad):
        os.remove(pfad)
    db.session.delete(bild)
    db.session.commit()
    audit_log('slider_bild_geloescht', {'datei': bild.original_name})
    flash('Bild gelöscht.', 'success')
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/slider/reihenfolge', methods=['POST'])
@admin_required
def slider_reihenfolge():
    """Reihenfolge der Slider-Bilder speichern (kommagetrennte IDs)."""
    ids = request.form.get('reihenfolge', '').split(',')
    for pos, bild_id in enumerate(ids):
        bild_id = bild_id.strip()
        if bild_id.isdigit():
            SliderBild.query.filter_by(id=int(bild_id)).update({'reihenfolge': pos * 10})
    db.session.commit()
    return ('', 204)


@admin_bp.route('/slider/bild/<gespeicherter_name>')
@admin_required
def slider_bild(gespeicherter_name):
    """Slider-Bild streamen (Admin-Vorschau)."""
    import mimetypes
    pfad = os.path.join(_slider_pfad(), gespeicherter_name)
    if not os.path.exists(pfad):
        from flask import abort
        abort(404)
    mime = mimetypes.guess_type(pfad)[0] or 'image/jpeg'
    with open(pfad, 'rb') as f:
        inhalt = f.read()
    return Response(inhalt, mimetype=mime)


# ─── Audit Log ───────────────────────────────────────────────────────────────

@admin_bp.route('/audit-log')
@admin_required
def audit_log_view():
    """Audit-Log filterbar nach Nutzer, Aktion, Datum."""
    # Filter aus Query-Parametern
    filter_user = request.args.get('user_id', type=int)
    filter_aktion = request.args.get('aktion', '').strip()
    filter_datum_von = request.args.get('von', '').strip()
    filter_datum_bis = request.args.get('bis', '').strip()

    query = AuditLog.query

    if filter_user:
        query = query.filter_by(user_id=filter_user)
    if filter_aktion:
        query = query.filter(AuditLog.aktion.ilike(f'%{filter_aktion}%'))
    if filter_datum_von:
        try:
            query = query.filter(AuditLog.erstellt_am >= datetime.strptime(filter_datum_von, '%Y-%m-%d'))
        except ValueError:
            pass
    if filter_datum_bis:
        try:
            query = query.filter(AuditLog.erstellt_am <= datetime.strptime(filter_datum_bis, '%Y-%m-%d') + timedelta(days=1))
        except ValueError:
            pass

    eintraege = query.order_by(AuditLog.erstellt_am.desc()).limit(500).all()
    alle_nutzer = User.query.order_by(User.name).all()

    return render_template('admin/audit_log.html',
                           eintraege=eintraege,
                           alle_nutzer=alle_nutzer,
                           filter_user=filter_user,
                           filter_aktion=filter_aktion)


@admin_bp.route('/audit-log/export')
@admin_required
def audit_log_export():
    """Audit-Log als CSV exportieren."""
    eintraege = AuditLog.query.order_by(AuditLog.erstellt_am.desc()).all()

    def generate():
        header = ['ID', 'Zeitstempel', 'User-ID', 'Aktion', 'Objekt-ID', 'IP', 'Details']
        yield ','.join(header) + '\n'
        for e in eintraege:
            row = [
                str(e.id),
                e.erstellt_am.strftime('%Y-%m-%d %H:%M:%S'),
                str(e.user_id or ''),
                e.aktion,
                str(e.objekt_id or ''),
                e.ip_adresse or '',
                (e.details or '').replace(',', ';')
            ]
            yield ','.join(row) + '\n'

    audit_log('audit_export')
    return Response(generate(), mimetype='text/csv',
                    headers={'Content-Disposition': 'attachment; filename=audit_log.csv'})
