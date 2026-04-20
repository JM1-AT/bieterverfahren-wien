import io
import math
import os
from functools import wraps
from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, current_app, send_file)
from flask_login import login_required, current_user
from models import db, Objekt, Dokument, Gebot, ObjektZugang, Zustimmung, ObjektFoto, SliderBild
from security import entschluesseln, upload_pfad, foto_pfad, sha256_hash, objekt_nda_pfad, objekt_nda_vorhanden
from mail import (mail_gebot_ueberboten, mail_gebot_bestaetigung)
from auth import audit_log
from i18n import t

bieter_bp = Blueprint('bieter', __name__, url_prefix='/bieter')

MIN_BID_INCREMENT = 1.03   # Jedes Folgegebot: mindestens +3%
MAX_BID_INCREMENT = 50_000  # aber maximal +50.000 €


# ─── Zugriffsschutz ─────────────────────────────────────────────────────────

def bieter_required(f):
    """Decorator: Nur für eingeloggte Bieter."""
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if current_user.rolle not in ('bieter', 'admin'):
            flash('Kein Zugang.', 'error')
            return redirect(url_for('auth.login'))
        if current_user.status != 'aktiv':
            flash('Ihr Konto ist nicht aktiv.', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


def _hat_zugang(user_id: int, objekt_id: int) -> bool:
    """Prüft ob der Bieter Zugang zu diesem Objekt hat."""
    return ObjektZugang.query.filter_by(
        user_id=user_id, objekt_id=objekt_id
    ).first() is not None


def _hat_nda_bestaetigt(user_id: int, objekt_id: int) -> bool:
    """Prüft ob der Bieter die NDA für dieses Objekt bestätigt hat."""
    return Zustimmung.query.filter_by(
        user_id=user_id, objekt_id=objekt_id
    ).first() is not None


# ─── Profil ─────────────────────────────────────────────────────────────────

@bieter_bp.route('/profil', methods=['GET', 'POST'])
@bieter_required
def profil():
    """Bieter-Profil anzeigen und bearbeiten."""
    if request.method == 'POST':
        current_user.name = request.form.get('name', '').strip() or current_user.name
        current_user.firma = request.form.get('firma', '').strip() or None
        current_user.firmenname = request.form.get('firmenname', '').strip() or None
        current_user.position = request.form.get('position', '').strip() or None
        current_user.adresse = request.form.get('adresse', '').strip() or None
        current_user.mobilnummer = request.form.get('mobilnummer', '').strip() or None
        current_user.benachrichtigung_email = 'benachrichtigung_email' in request.form
        current_user.benachrichtigung_sms = 'benachrichtigung_sms' in request.form
        current_user.benachrichtigung_push = 'benachrichtigung_push' in request.form
        db.session.commit()
        flash('Profil gespeichert.', 'success')
        return redirect(url_for('bieter.profil'))
    return render_template('bieter/profil.html')


# ─── Dashboard ──────────────────────────────────────────────────────────────

@bieter_bp.route('/')
@bieter_bp.route('/dashboard')
@bieter_required
def dashboard():
    """Bieter-Dashboard: Liste der zugänglichen Objekte."""
    # Alle Objekte mit Zugang für diesen Bieter
    zugaenge = ObjektZugang.query.filter_by(user_id=current_user.id).all()
    objekt_ids = [z.objekt_id for z in zugaenge]
    objekte = Objekt.query.filter(
        Objekt.id.in_(objekt_ids), Objekt.veroeffentlicht == True
    ).all() if objekt_ids else []

    # NDA-Status pro Objekt
    objekte_info = []
    for obj in objekte:
        nda_ok = _hat_nda_bestaetigt(current_user.id, obj.id)
        hoechstgebot = obj.hoechstgebot()
        objekte_info.append({
            'objekt': obj,
            'nda_ok': nda_ok,
            'hoechstgebot': hoechstgebot
        })

    slider_bilder = SliderBild.query.order_by(SliderBild.reihenfolge).all()
    return render_template('bieter/dashboard.html', objekte_info=objekte_info, slider_bilder=slider_bilder)


# ─── Objektdetail ────────────────────────────────────────────────────────────

@bieter_bp.route('/objekt/<int:objekt_id>')
@bieter_required
def objekt_detail(objekt_id):
    """Objektdetail für Bieter – NDA-Gate."""
    objekt = Objekt.query.get_or_404(objekt_id)

    # Zugang prüfen
    if not _hat_zugang(current_user.id, objekt_id):
        flash('Sie haben keinen Zugang zu diesem Objekt.', 'error')
        return redirect(url_for('bieter.dashboard'))

    # Nur veröffentlichte Objekte für Bieter sichtbar
    if not objekt.veroeffentlicht:
        flash('Dieses Verfahren ist noch nicht freigegeben.', 'error')
        return redirect(url_for('bieter.dashboard'))

    # NDA prüfen – Modal anzeigen wenn nicht bestätigt
    nda_bestaetigt = _hat_nda_bestaetigt(current_user.id, objekt_id)
    if not nda_bestaetigt:
        from flask import session
        lang = session.get('lang', 'de')
        nda_text = current_app.config['NDA_TEXT'].get(lang, current_app.config['NDA_TEXT']['de'])
        return render_template('bieter/nda_modal.html',
                               objekt=objekt,
                               nda_text=nda_text,
                               nda_pdf=objekt_nda_vorhanden(objekt_id),
                               nda_version=current_app.config['NDA_VERSION'])

    # Höchstgebot, Dokumente und Fotos
    hoechstgebot = objekt.hoechstgebot()
    dokumente = Dokument.query.filter_by(objekt_id=objekt_id).all()
    fotos = ObjektFoto.query.filter_by(objekt_id=objekt_id).order_by(ObjektFoto.reihenfolge).all()

    # Mindestgebot berechnen
    if hoechstgebot is None:
        mindestgebot = int(objekt.startpreis)
    else:
        zuschlag = min(math.ceil(hoechstgebot * MIN_BID_INCREMENT) - hoechstgebot, MAX_BID_INCREMENT)
        mindestgebot = int(hoechstgebot) + int(zuschlag)

    rendite = objekt.rendite_berechnen(hoechstgebot)

    # Nebenkosten berechnen (auf Basis Höchstgebot oder Startpreis)
    basis = hoechstgebot or objekt.startpreis
    nebenkosten = _nebenkosten_berechnen(objekt, basis)

    audit_log('objekt_ansicht', {'objekt': objekt.titel}, objekt_id=objekt_id)

    return render_template('bieter/objekt_detail.html',
                           objekt=objekt,
                           hoechstgebot=hoechstgebot,
                           mindestgebot=mindestgebot,
                           rendite=rendite,
                           dokumente=dokumente,
                           fotos=fotos,
                           nebenkosten=nebenkosten)


def _nebenkosten_berechnen(objekt: Objekt, kaufpreis: float) -> dict:
    """Nebenkosten auf Basis Kaufpreis berechnen."""
    provision = kaufpreis * (objekt.maklerprovision / 100) if not objekt.gew_nebenkosten_ausblenden else 0
    notar = kaufpreis * (objekt.notarkosten / 100)
    grunderwerb = kaufpreis * (objekt.grunderwerbssteuer / 100)
    grundbuch = kaufpreis * (objekt.grundbuch_gebuehr / 100) if not objekt.gb_nebenkosten_ausblenden else 0
    gesamt = provision + notar + grunderwerb + grundbuch
    return {
        'provision': provision,
        'notar': notar,
        'grunderwerb': grunderwerb,
        'grundbuch': grundbuch,
        'gesamt': gesamt
    }


# ─── NDA Bestätigung ─────────────────────────────────────────────────────────

@bieter_bp.route('/objekt/<int:objekt_id>/nda-bestaetigen', methods=['POST'])
@bieter_required
def nda_bestaetigen(objekt_id):
    """NDA-Bestätigung speichern – mit Zeitstempel, IP, UA, SHA256-Hash."""
    objekt = Objekt.query.get_or_404(objekt_id)

    # Zugang prüfen
    if not _hat_zugang(current_user.id, objekt_id):
        flash('Kein Zugang.', 'error')
        return redirect(url_for('bieter.dashboard'))

    # Bereits bestätigt?
    if _hat_nda_bestaetigt(current_user.id, objekt_id):
        return redirect(url_for('bieter.objekt_detail', objekt_id=objekt_id))

    # Alle 3 Checkboxen müssen gesetzt sein
    check1 = request.form.get('check1')
    check2 = request.form.get('check2')
    check3 = request.form.get('check3')

    if not (check1 and check2 and check3):
        flash(t('fehler_nda'), 'error')
        return redirect(url_for('bieter.objekt_detail', objekt_id=objekt_id))

    # Scroll-Bestätigung prüfen (Client setzt scrolled=1)
    scrolled = request.form.get('scrolled', '0')
    if scrolled != '1':
        flash('Bitte lesen Sie den gesamten Text.', 'error')
        return redirect(url_for('bieter.objekt_detail', objekt_id=objekt_id))

    # NDA-Text hash berechnen
    from flask import session
    lang = session.get('lang', 'de')
    nda_text = current_app.config['NDA_TEXT'].get(lang, current_app.config['NDA_TEXT']['de'])
    text_hash = sha256_hash(nda_text)

    # Zustimmung speichern
    zustimmung = Zustimmung(
        user_id=current_user.id,
        objekt_id=objekt_id,
        ip_adresse=request.remote_addr,
        user_agent=request.user_agent.string[:500] if request.user_agent else None,
        version=current_app.config['NDA_VERSION'],
        text_hash=text_hash
    )
    db.session.add(zustimmung)
    db.session.commit()

    audit_log('nda_bestaetigt', {
        'objekt': objekt.titel,
        'version': current_app.config['NDA_VERSION'],
        'hash': text_hash
    }, objekt_id=objekt_id)

    flash(t('erfolg_nda'), 'success')
    return redirect(url_for('bieter.objekt_detail', objekt_id=objekt_id))


# ─── Gebot abgeben ───────────────────────────────────────────────────────────

@bieter_bp.route('/objekt/<int:objekt_id>/gebot', methods=['POST'])
@bieter_required
def gebot_abgeben(objekt_id):
    """Verbindliches Gebot abgeben."""
    objekt = Objekt.query.get_or_404(objekt_id)

    # Zugang + NDA prüfen
    if not _hat_zugang(current_user.id, objekt_id):
        flash('Kein Zugang.', 'error')
        return redirect(url_for('bieter.dashboard'))

    if not _hat_nda_bestaetigt(current_user.id, objekt_id):
        flash('Bitte bestätigen Sie zuerst die NDA.', 'error')
        return redirect(url_for('bieter.objekt_detail', objekt_id=objekt_id))

    # Verfahren aktiv?
    if not objekt.ist_aktiv():
        flash('Das Bieterverfahren ist nicht mehr aktiv.', 'error')
        return redirect(url_for('bieter.objekt_detail', objekt_id=objekt_id))

    # Betrag validieren
    try:
        betrag = int(request.form.get('betrag', '').replace('.', '').replace(',', '').strip())
    except (ValueError, AttributeError):
        flash(t('fehler_gebot'), 'error')
        return redirect(url_for('bieter.objekt_detail', objekt_id=objekt_id))

    # Mindestgebot: Startpreis erlaubt, danach +3% pro Runde
    hoechstgebot = objekt.hoechstgebot()
    if hoechstgebot is None:
        if betrag < int(objekt.startpreis):
            flash(t('fehler_gebot'), 'error')
            return redirect(url_for('bieter.objekt_detail', objekt_id=objekt_id))
    else:
        zuschlag = min(math.ceil(hoechstgebot * MIN_BID_INCREMENT) - hoechstgebot, MAX_BID_INCREMENT)
        mindest = int(hoechstgebot) + int(zuschlag)
        if betrag < mindest:
            flash(t('fehler_gebot'), 'error')
            return redirect(url_for('bieter.objekt_detail', objekt_id=objekt_id))

    # Mindestspread-Validierung (fixer €-Betrag, überschreibt prozentuales Minimum wenn gesetzt)
    if objekt.mindestspread and objekt.mindestspread > 0 and hoechstgebot is not None:
        mindest_spread = int(hoechstgebot + objekt.mindestspread)
        if betrag < mindest_spread:
            flash(f'Mindestgebot: € {mindest_spread:,}'.replace(',', '.'), 'error')
            return redirect(url_for('bieter.objekt_detail', objekt_id=objekt_id))

    # Binding-Bestätigung prüfen (falls nicht ausgeblendet)
    if not objekt.binding_bestaetigung_ausblenden:
        if not request.form.get('binding'):
            flash('Bitte bestätigen Sie, dass Ihr Gebot rechtlich bindend ist.', 'error')
            return redirect(url_for('bieter.objekt_detail', objekt_id=objekt_id))

    # Vorherigen Höchstbieter ermitteln (für Überbietungs-Mail)
    vorheriger_hoechstbieter = None
    if hoechstgebot:
        vorheriges_gebot = Gebot.query.filter_by(objekt_id=objekt_id).order_by(
            Gebot.betrag.desc()
        ).first()
        if vorheriges_gebot and vorheriges_gebot.user_id != current_user.id:
            vorheriger_hoechstbieter = vorheriges_gebot.bieter

    # Gebot speichern
    gebot = Gebot(
        objekt_id=objekt_id,
        user_id=current_user.id,
        betrag=betrag,
        ip_adresse=request.remote_addr
    )
    db.session.add(gebot)
    db.session.commit()

    audit_log('gebot_abgegeben', {'betrag': betrag}, objekt_id=objekt_id)

    # Bestätigungs-Mail an Bieter
    mail_gebot_bestaetigung(current_user.email, current_user.name, objekt.titel, betrag)

    # Überbietungs-Mail an vorherigen Höchstbieter (kein Name!)
    if vorheriger_hoechstbieter:
        mail_gebot_ueberboten(
            vorheriger_hoechstbieter.email,
            vorheriger_hoechstbieter.name,
            objekt.titel,
            betrag
        )

    flash(t('erfolg_gebot'), 'success')
    return redirect(url_for('bieter.objekt_detail', objekt_id=objekt_id))


# ─── Dokument-Download ───────────────────────────────────────────────────────

@bieter_bp.route('/dokument/<int:dok_id>')
@bieter_required
def dokument_download(dok_id):
    """Verschlüsseltes Dokument entschlüsseln und streamen – nur mit Zugang + NDA."""
    dok = Dokument.query.get_or_404(dok_id)

    # Zugang prüfen
    if not _hat_zugang(current_user.id, dok.objekt_id):
        flash('Kein Zugang.', 'error')
        return redirect(url_for('bieter.dashboard'))

    # NDA prüfen
    if not _hat_nda_bestaetigt(current_user.id, dok.objekt_id):
        flash('Bitte bestätigen Sie zuerst die NDA.', 'error')
        return redirect(url_for('bieter.objekt_detail', objekt_id=dok.objekt_id))

    # Datei lesen und entschlüsseln
    pfad = os.path.join(upload_pfad(dok.objekt_id), dok.gespeicherter_name)
    if not os.path.exists(pfad):
        flash('Dokument nicht gefunden.', 'error')
        return redirect(url_for('bieter.objekt_detail', objekt_id=dok.objekt_id))

    with open(pfad, 'rb') as f:
        verschluesselt_inhalt = f.read()

    inhalt = entschluesseln(verschluesselt_inhalt)

    audit_log('dokument_download', {
        'datei': dok.original_name,
        'objekt_id': dok.objekt_id
    }, objekt_id=dok.objekt_id)

    als_download = request.args.get('download') == '1'
    return send_file(
        io.BytesIO(inhalt),
        download_name=dok.original_name,
        as_attachment=als_download
    )


# ─── Slider-Bild Stream ──────────────────────────────────────────────────────

@bieter_bp.route('/slider/<gespeicherter_name>')
@bieter_required
def slider_bild(gespeicherter_name):
    """Slider-Bild streamen – nur für eingeloggte Bieter."""
    import mimetypes
    from flask import Response, abort
    import os as _os
    pfad = _os.path.join(_os.path.dirname(__file__), 'uploads', 'slider', gespeicherter_name)
    if not _os.path.exists(pfad):
        abort(404)
    mime = mimetypes.guess_type(pfad)[0] or 'image/jpeg'
    with open(pfad, 'rb') as f:
        inhalt = f.read()
    return Response(inhalt, mimetype=mime)


# ─── NDA-PDF Stream ──────────────────────────────────────────────────────────

@bieter_bp.route('/objekt/<int:objekt_id>/nda-pdf')
@bieter_required
def nda_pdf(objekt_id):
    """Objektspezifisches NDA-PDF streamen – nur mit Zugang."""
    from flask import Response, abort
    if not _hat_zugang(current_user.id, objekt_id):
        abort(403)
    pfad = objekt_nda_pfad(objekt_id)
    if not os.path.exists(pfad):
        abort(404)
    with open(pfad, 'rb') as f:
        inhalt = f.read()
    als_download = request.args.get('download') == '1'
    disposition = 'attachment' if als_download else 'inline'
    return Response(inhalt, mimetype='application/pdf',
                    headers={'Content-Disposition': f'{disposition}; filename=NDA_Bieterbedingungen.pdf'})


# ─── Foto-Stream ─────────────────────────────────────────────────────────────

@bieter_bp.route('/objekt/<int:objekt_id>/fotos/<gespeicherter_name>')
@bieter_required
def foto_ansehen(objekt_id, gespeicherter_name):
    """Foto streamen – nur mit Zugang zum Objekt."""
    import mimetypes
    from flask import Response, abort

    # Zugang prüfen
    if not _hat_zugang(current_user.id, objekt_id):
        abort(403)

    pfad = os.path.join(foto_pfad(objekt_id), gespeicherter_name)
    if not os.path.exists(pfad):
        abort(404)

    mime = mimetypes.guess_type(pfad)[0] or 'image/jpeg'
    with open(pfad, 'rb') as f:
        inhalt = f.read()
    return Response(inhalt, mimetype=mime)
