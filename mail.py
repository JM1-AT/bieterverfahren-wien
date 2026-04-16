import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app
from datetime import datetime


def _print_mail(betreff, empfaenger, inhalt):
    """Console-Ausgabe im Test-Modus."""
    print('\n' + '='*60)
    print(f'📧 E-MAIL (TEST-MODUS)')
    print(f'   An:      {empfaenger}')
    print(f'   Betreff: {betreff}')
    print(f'   Zeit:    {datetime.now().strftime("%d.%m.%Y %H:%M:%S")}')
    print('-'*60)
    print(inhalt)
    print('='*60 + '\n')


def _send_mail(betreff, empfaenger, inhalt):
    """E-Mail senden – SMTP in Produktion, Console im Test-Modus."""
    if current_app.config.get('MAIL_TEST_MODE', True):
        _print_mail(betreff, empfaenger, inhalt)
        return

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = betreff
        msg['From']    = current_app.config['MAIL_DEFAULT_SENDER']
        msg['To']      = empfaenger
        msg.attach(MIMEText(inhalt, 'plain', 'utf-8'))

        server = smtplib.SMTP(
            current_app.config['MAIL_SERVER'],
            current_app.config['MAIL_PORT'],
            timeout=10
        )
        server.ehlo()
        server.starttls()
        server.login(
            current_app.config['MAIL_USERNAME'],
            current_app.config['MAIL_PASSWORD']
        )
        server.sendmail(
            current_app.config['MAIL_DEFAULT_SENDER'],
            empfaenger,
            msg.as_string()
        )
        server.quit()
        print(f'[Mail] ✓ Gesendet an {empfaenger}: {betreff}')
    except Exception as e:
        print(f'[Mail] ✗ Fehler beim Senden an {empfaenger}: {e}')
        _print_mail(betreff, empfaenger, inhalt)


def mail_verfahren_startet(bieter_email, bieter_name, objekt_titel, startpreis, ende):
    """1. Verfahren startet → alle Bieter des Objekts."""
    betreff = f'Bieterverfahren gestartet: {objekt_titel}'
    inhalt = f"""Sehr geehrte/r {bieter_name},

das Bieterverfahren für folgendes Objekt hat begonnen:

Objekt:    {objekt_titel}
Startpreis: € {startpreis:,.0f}
Laufzeit:  bis {ende.strftime('%d.%m.%Y %H:%M') if ende else 'offen'}

Melden Sie sich auf der Plattform an, um Ihre Unterlagen einzusehen und ein Gebot abzugeben.

Mit freundlichen Grüßen
Bieterverfahren Wien"""
    _send_mail(betreff, bieter_email, inhalt)


def mail_gebot_ueberboten(bieter_email, bieter_name, objekt_titel, neues_hoechstgebot):
    """2. Gebot überboten → nur der überbotene Bieter (kein Name des neuen Bieters!)."""
    betreff = f'Ihr Gebot wurde überboten – {objekt_titel}'
    inhalt = f"""Sehr geehrte/r {bieter_name},

Ihr Gebot für folgendes Objekt wurde überboten:

Objekt:            {objekt_titel}
Aktuelles Höchstgebot: € {neues_hoechstgebot:,.0f}

Möchten Sie ein neues Gebot abgeben? Melden Sie sich auf der Plattform an.

(Der Name des Bieters wird aus Vertraulichkeitsgründen nicht bekannt gegeben.)

Mit freundlichen Grüßen
Bieterverfahren Wien"""
    _send_mail(betreff, bieter_email, inhalt)


def mail_verfahren_endet_bald(bieter_email, bieter_name, objekt_titel, hoechstgebot, ende):
    """3. Verfahren endet in 24h → alle Bieter."""
    betreff = f'Bieterverfahren endet in 24 Stunden: {objekt_titel}'
    aktuell = f'€ {hoechstgebot:,.0f}' if hoechstgebot else 'Noch kein Gebot'
    inhalt = f"""Sehr geehrte/r {bieter_name},

das Bieterverfahren endet morgen:

Objekt:              {objekt_titel}
Verfahrensende:      {ende.strftime('%d.%m.%Y %H:%M') if ende else 'offen'}
Aktuelles Höchstgebot: {aktuell}

Dies ist Ihre letzte Möglichkeit, ein Gebot abzugeben.

Mit freundlichen Grüßen
Bieterverfahren Wien"""
    _send_mail(betreff, bieter_email, inhalt)


def mail_verfahren_beendet_bieter(bieter_email, bieter_name, objekt_titel, hoechstgebot):
    """4a. Verfahren beendet → alle Bieter (ohne Gewinnername)."""
    betreff = f'Bieterverfahren beendet: {objekt_titel}'
    endgebot = f'€ {hoechstgebot:,.0f}' if hoechstgebot else 'Kein Gebot eingegangen'
    inhalt = f"""Sehr geehrte/r {bieter_name},

das Bieterverfahren für folgendes Objekt ist beendet:

Objekt:   {objekt_titel}
Endgebot: {endgebot}

Vielen Dank für Ihre Teilnahme. Bei Fragen wenden Sie sich bitte an unser Büro.

Mit freundlichen Grüßen
Bieterverfahren Wien
RA Mag. Werner Maierhofer"""
    _send_mail(betreff, bieter_email, inhalt)


def mail_verfahren_beendet_admin(admin_email, objekt_titel, hoechstgebot,
                                  gewinner_name, gewinner_email, gewinner_firma,
                                  anzahl_gebote):
    """4b. Verfahren beendet → Admin-Mail mit Gewinner-Details."""
    betreff = f'[ADMIN] Verfahren beendet: {objekt_titel}'
    endgebot = f'€ {hoechstgebot:,.0f}' if hoechstgebot else 'Kein Gebot eingegangen'
    inhalt = f"""ADMIN-BERICHT: Bieterverfahren beendet

Objekt:          {objekt_titel}
Endgebot:        {endgebot}
Anzahl Gebote:   {anzahl_gebote}

GEWINNER:
Name:    {gewinner_name or '–'}
E-Mail:  {gewinner_email or '–'}
Firma:   {gewinner_firma or '–'}

Bitte nehmen Sie Kontakt mit dem Gewinner auf."""
    _send_mail(betreff, admin_email, inhalt)


def mail_einladung(empfaenger_email, empfaenger_name, einladungslink):
    """5. Einladung → Einladungslink (72h gültig)."""
    betreff = 'Einladung zur Bieterplattform Wien'
    inhalt = f"""Sehr geehrte/r {empfaenger_name},

Sie wurden zur Bieterverfahren Wien Plattform eingeladen.

Bitte klicken Sie auf folgenden Link, um Ihren Zugang einzurichten:

{einladungslink}

Dieser Link ist 72 Stunden gültig.

Bei Fragen stehen wir Ihnen gerne zur Verfügung.

Mit freundlichen Grüßen
Bieterverfahren Wien
RA Mag. Werner Maierhofer"""
    _send_mail(betreff, empfaenger_email, inhalt)


def mail_anfrage_bestaetigt(empfaenger_email, empfaenger_name, einladungslink):
    """6. Anfrage bestätigt → Einladungslink zur Passwort-Erstellung."""
    betreff = 'Ihr Zugang wurde freigeschaltet – Bieterverfahren Wien'
    inhalt = f"""Sehr geehrte/r {empfaenger_name},

Ihre Zugriffsanfrage wurde genehmigt.

Bitte legen Sie jetzt Ihr Passwort fest:

{einladungslink}

Dieser Link ist 72 Stunden gültig.

Mit freundlichen Grüßen
Bieterverfahren Wien
RA Mag. Werner Maierhofer"""
    _send_mail(betreff, empfaenger_email, inhalt)


def mail_anfrage_abgelehnt(empfaenger_email, empfaenger_name):
    """7. Anfrage abgelehnt → höfliche Ablehnung."""
    betreff = 'Ihre Anfrage – Bieterverfahren Wien'
    inhalt = f"""Sehr geehrte/r {empfaenger_name},

vielen Dank für Ihr Interesse an Bieterverfahren Wien.

Nach Prüfung Ihrer Anfrage müssen wir Ihnen leider mitteilen, dass wir Ihren Zugang derzeit nicht freischalten können.

Bei Fragen wenden Sie sich bitte direkt an unser Büro.

Mit freundlichen Grüßen
Bieterverfahren Wien
RA Mag. Werner Maierhofer"""
    _send_mail(betreff, empfaenger_email, inhalt)


def mail_passwort_reset(empfaenger_email, empfaenger_name, reset_link):
    """9. Passwort-Reset-Link senden (gültig 1 Stunde)."""
    betreff = 'Passwort zurücksetzen – Bieterverfahren Wien'
    inhalt = f"""Sehr geehrte/r {empfaenger_name},

Sie haben eine Anfrage zum Zurücksetzen Ihres Passworts gestellt.

Bitte klicken Sie auf folgenden Link, um ein neues Passwort zu vergeben:

{reset_link}

Dieser Link ist 1 Stunde gültig. Falls Sie keine Anfrage gestellt haben, können Sie diese E-Mail ignorieren.

Mit freundlichen Grüßen
Bieterverfahren Wien
RA Mag. Werner Maierhofer"""
    _send_mail(betreff, empfaenger_email, inhalt)


def mail_gebot_bestaetigung(bieter_email, bieter_name, objekt_titel, betrag):
    """8. Gebot bestätigt → Bieter bekommt Bestätigung seines Gebots."""
    betreff = f'Gebot bestätigt: {objekt_titel}'
    inhalt = f"""Sehr geehrte/r {bieter_name},

Ihr Gebot wurde erfolgreich registriert:

Objekt:    {objekt_titel}
Ihr Gebot: € {betrag:,.0f}

Bitte beachten Sie: Dieses Gebot ist rechtlich bindend.
Sie werden benachrichtigt, falls Ihr Gebot überboten wird.

Mit freundlichen Grüßen
Bieterverfahren Wien
RA Mag. Werner Maierhofer"""
    _send_mail(betreff, bieter_email, inhalt)
