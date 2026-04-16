from flask import current_app
from datetime import datetime


def _print_mail(betreff, empfaenger, inhalt):
    """Test-Modus: E-Mail in Console ausgeben statt senden."""
    print('\n' + '='*60)
    print(f'📧 E-MAIL (TEST-MODUS)')
    print(f'   An:      {empfaenger}')
    print(f'   Betreff: {betreff}')
    print(f'   Zeit:    {datetime.now().strftime("%d.%m.%Y %H:%M:%S")}')
    print('-'*60)
    print(inhalt)
    print('='*60 + '\n')


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
    _print_mail(betreff, bieter_email, inhalt)


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
    _print_mail(betreff, bieter_email, inhalt)


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
    _print_mail(betreff, bieter_email, inhalt)


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
    _print_mail(betreff, bieter_email, inhalt)


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
    _print_mail(betreff, admin_email, inhalt)


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
    _print_mail(betreff, empfaenger_email, inhalt)


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
    _print_mail(betreff, empfaenger_email, inhalt)


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
    _print_mail(betreff, empfaenger_email, inhalt)


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
    _print_mail(betreff, empfaenger_email, inhalt)


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
    _print_mail(betreff, bieter_email, inhalt)
