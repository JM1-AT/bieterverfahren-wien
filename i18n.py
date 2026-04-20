from flask import session

# Übersetzungswörterbuch DE + EN
T = {
    'de': {
        # Navigation
        'nav_ablauf':        'Ablauf',
        'nav_faq':           'FAQ',
        'nav_kontakt':       'Kontakt',
        'nav_abmelden':      'Abmelden',

        # Landing / Login
        'hero_label':        'Bieterverfahren Wien',
        'hero_h1':           'Professionelle Bieterverfahren.\nTransparent & Sicher.',
        'hero_sub':          'Bieterverfahren Wien begleitet Sie durch das gesamte Verfahren und ermöglicht mit der hauseigenen Software einen sicheren und digitalen Verkaufsprozess.',
        'login_label':       'Zugang zur Plattform',
        'login_email':       'E-Mail',
        'login_passwort':    'Passwort',
        'login_btn':         'Einloggen',
        'login_google':      'Mit Google anmelden',
        'login_anfrage':     'Neu hier? Zugang anfragen →',

        # Ablauf-Schritte
        'step1_num':         '01',
        'step1_title':       'Zugang anfragen',
        'step1_text':        'Registrierung beantragen oder Einladung vom Admin erhalten',
        'step2_num':         '02',
        'step2_title':       'NDA bestätigen',
        'step2_text':        'Vertraulichkeitserklärung & Bieterbedingungen unterzeichnen',
        'step3_num':         '03',
        'step3_title':       'Objekt einsehen',
        'step3_text':        'Dokumente, Details und Unterlagen herunterladen & prüfen',
        'step4_num':         '04',
        'step4_title':       'Gebot abgeben',
        'step4_text':        'Verbindliches Angebot über Startpreis einreichen',

        # Anfrage
        'anfrage_titel':     'Zugang anfragen',
        'anfrage_name':      'Name',
        'anfrage_email':     'E-Mail',
        'anfrage_firma':     'Unternehmen',
        'anfrage_begruendung': 'Begründung / Interesse',
        'anfrage_btn':       'Anfrage senden',
        'anfrage_success':   'Ihre Anfrage wurde gesendet. Wir melden uns.',

        # Einladung
        'einladung_titel':   'Passwort festlegen',
        'einladung_sub':     'Bitte legen Sie ein Passwort für Ihren Zugang fest.',
        'einladung_pw':      'Passwort',
        'einladung_pw2':     'Passwort bestätigen',
        'einladung_btn':     'Zugang aktivieren',
        'einladung_abgelaufen': 'Dieser Einladungslink ist abgelaufen oder ungültig.',

        # NDA Modal
        'nda_titel':         'Vertraulichkeitserklärung & Bieterbedingungen',
        'nda_sub':           'Pflichtlektüre vor Objektzugang · kein Schließen ohne Bestätigung',
        'nda_scroll_hint':   '↓ Bitte vollständig lesen um fortzufahren',
        'nda_check1':        'Ich habe die Bieterbedingungen vollständig gelesen und verstanden.',
        'nda_check2':        'Ich verpflichte mich zur Vertraulichkeit gemäß der obigen NDA.',
        'nda_check3':        'Mir ist bewusst, dass abgegebene Gebote rechtlich bindend sind.',
        'nda_btn':           'Verbindlich bestätigen & Objekt einsehen',
        'nda_note':          'Diese Bestätigung wird mit Zeitstempel und IP-Adresse protokolliert',

        # Bieter Dashboard
        'bieter_titel':      'Aktive Verfahren',
        'meine_verfahren':   'Meine Verfahren',
        'hoechstgebot':      'Höchstgebot',
        'startpreis':        'Startpreis',
        'endet_in':          'Verfahren endet in',
        'dokumente':         'Dokumente',
        'download':          '↓ Download',
        'gebot_label':       'Gebot abgeben',
        'gebot_hint':        'Mindestgebot: über aktuellem Höchstgebot',
        'gebot_check':       'Mein Gebot ist rechtlich bindend.',
        'gebot_btn':         'Gebot verbindlich abgeben',
        'nda_ausstehend':    'NDA erforderlich',
        'noch_kein_gebot':   'Noch kein Gebot',
        'tage':              'Tage',
        'stunden':           'Std',
        'minuten':           'Min',
        'sekunden':          'Sek',

        # Nebenkosten
        'nebenkosten':       'Nebenkosten',
        'maklerprovision':   'Maklerprovision',
        'notarkosten':       'Notarkosten',
        'grunderwerbssteuer': 'Grunderwerbssteuer',
        'grundbucheintragung': 'Grundbucheintragung',
        'gesamt_nebenkosten': 'Geschätzte Nebenkosten',

        # Admin
        'admin_dashboard':   'Dashboard',
        'admin_objekte':     'Objekte',
        'admin_bieter':      'Bieter',
        'admin_anfragen':    'Anfragen',
        'admin_nda':         'NDA Nachweise',
        'admin_einladungen': 'Einladungen',
        'admin_nutzer':      'Nutzer',
        'admin_audit':       'Audit Log',
        'admin_einstellungen': 'Einstellungen',
        'bestaetigen':       'Bestätigen',
        'ablehnen':          'Ablehnen',
        'einladen':          'Einladen',
        'neu_anlegen':       'Neu anlegen',
        'speichern':         'Speichern',
        'loeschen':          'Löschen',
        'exportieren':       'Exportieren',
        'alle_ansehen':      'Alle ansehen',
        'pdf_export':        'PDF Export',
        'csv_export':        'CSV Export',

        # Status
        'aktiv':             'Aktiv',
        'ausstehend':        'Ausstehend',
        'abgelehnt':         'Abgelehnt',
        'endet_bald':        'Endet bald',
        'vorbereitung':      'Vorbereitung',
        'beendet':           'Beendet',
        'bestaetigt':        '✔ Bestätigt',
        'nda_bestaetigt':    '✔ Bestätigt',
        'nda_ausstehend_status': '⏳ Ausstehend',

        # Admin Metriken
        'aktive_objekte':    'Aktive Objekte',
        'aktive_bieter':     'Aktive Bieter',
        'offene_anfragen':   'Offene Anfragen',
        'nda_bestaetigt_ratio': 'NDA Bestätigt',
        'aktive_verfahren':  'Aktive Verfahren',
        'offene_anfragen_card': 'Offene Anfragen',

        # Admin Objekt
        'geschaeftsbeziehung': 'Geschäftsbeziehung',
        'titel_immobilie':   'Titel Immobilie',
        'objektnummer':      'Objektnummer',
        'flaeche_m2':        'Fläche in m²',
        'strasse':           'Straße',
        'plz':               'PLZ',
        'ort':               'Ort',
        'land':              'Land',
        'beschreibung':      'Beschreibung',
        'link_detail':       'Link Detailbeschreibung',
        'link_3d':           'Link 3D-Rundgang',
        'beginn':            'Beginn',
        'ende':              'Ende',
        'startpreis_label':  'Startpreis (€)',
        'zielpreis_label':   'Zielpreis intern (€)',
        'sofortkauf':        'Sofortkauf-Option',
        'sofortkauf_preis':  'Sofortkauf-Preis (€)',
        'provision_label':   'Maklerprovision (%)',
        'notar_label':       'Notarkosten (%)',
        'grunderwerb_label': 'Grunderwerbssteuer (%)',
        'gb_label':          'Grundbucheintragung (%)',
        'nebenkosten_ausbl': 'Nebenkosten ausblenden',
        'gb_nebenkosten_ausbl': 'GB-Nebenkosten ausblenden',
        'zusatzvereinbarungen': 'Zusatzvereinbarungen',
        'binding_ausbl':     'Binding-Bestätigung ausblenden',
        'angebotsliste_ausbl': 'Angebotsliste ausblenden',
        'jetzt':             'Jetzt',
        'in_1_woche':        '+1 Woche',
        'in_2_wochen':       '+2 Wochen',
        'in_3_wochen':       '+3 Wochen',

        # FAQ
        'faq_titel':         'Häufige Fragen',
        'wie_funktioniert_q': 'Wie funktioniert das Bieterverfahren?',
        'wie_funktioniert_a': 'Strukturierter Verkaufsprozess für Zinshäuser: Interessenten geben verbindliche Gebote ab. Nur das aktuelle Höchstgebot ist sichtbar – keine Namen, keine Bieteranzahl.',
        'zugang_q':          'Wie erhalte ich Zugang?',
        'zugang_a':          'Zugang nur auf Einladung oder nach Prüfung durch den Admin. Nach Freischaltung müssen NDA und Bieterbedingungen bestätigt werden.',
        'bindend_q':         'Sind Gebote rechtlich bindend?',
        'bindend_a':         'Ja. Alle Gebote sind rechtlich bindend. Die Kaufvertragserstellung und Treuhandschaft erfolgt durch RA Mag. Werner Maierhofer.',
        'wer_q':             'Wer steht hinter der Plattform?',
        'wer_a':             'Bieterverfahren Wien ist eine Serviceleistung von RA Mag. Werner Maierhofer, Spezialist für Zinshaustransaktionen.',

        # Footer
        'footer_copyright':  '© 2025 Bieterverfahren Wien',
        'footer_link':       'bieterverfahrenwien.at ↗',

        # 2FA
        '2fa_titel':         'Zwei-Faktor-Authentifizierung einrichten',
        '2fa_anleitung':     'Scannen Sie den QR-Code mit Google Authenticator oder einer kompatiblen App.',
        '2fa_code':          '6-stelliger Code',
        '2fa_btn':           '2FA aktivieren',
        '2fa_verify_titel':  'Zwei-Faktor-Authentifizierung',
        '2fa_verify_sub':    'Bitte geben Sie den Code aus Ihrer Authenticator-App ein.',
        '2fa_verify_btn':    'Code bestätigen',

        # Fehlermeldungen
        'fehler_login':      'E-Mail oder Passwort falsch.',
        'fehler_2fa':        'Ungültiger Code. Bitte versuchen Sie es erneut.',
        'fehler_upload':     'Datei nicht erlaubt oder zu groß (max. 20 MB).',
        'fehler_gebot':      'Ihr Gebot muss über dem aktuellen Höchstgebot liegen.',
        'fehler_nda':        'Bitte bestätigen Sie alle Bedingungen.',
        'erfolg_gebot':      'Ihr Gebot wurde erfolgreich abgegeben.',
        'erfolg_nda':        'NDA bestätigt. Sie können das Objekt nun einsehen.',
    },

    'en': {
        # Navigation
        'nav_ablauf':        'Process',
        'nav_faq':           'FAQ',
        'nav_kontakt':       'Contact',
        'nav_abmelden':      'Sign out',

        # Landing / Login
        'hero_label':        'Bieterverfahren Wien',
        'hero_h1':           'Professional Bidding Procedures.\nTransparent & Secure.',
        'hero_sub':          'Bieterverfahren Wien guides you through the entire procedure and enables a secure and digital sales process with its proprietary software.',
        'login_label':       'Platform Access',
        'login_email':       'Email',
        'login_passwort':    'Password',
        'login_btn':         'Sign in',
        'login_google':      'Sign in with Google',
        'login_anfrage':     'New here? Request access →',

        # Process steps
        'step1_num':         '01',
        'step1_title':       'Request access',
        'step1_text':        'Submit registration or receive an invitation from the admin',
        'step2_num':         '02',
        'step2_title':       'Confirm NDA',
        'step2_text':        'Sign confidentiality agreement & bidding terms',
        'step3_num':         '03',
        'step3_title':       'View property',
        'step3_text':        'Download and review documents and details',
        'step4_num':         '04',
        'step4_title':       'Place bid',
        'step4_text':        'Submit a legally binding offer above the starting price',

        # Request
        'anfrage_titel':     'Request access',
        'anfrage_name':      'Name',
        'anfrage_email':     'Email',
        'anfrage_firma':     'Company',
        'anfrage_begruendung': 'Reason for interest',
        'anfrage_btn':       'Send request',
        'anfrage_success':   'Your request has been sent. We will be in touch.',

        # Invitation
        'einladung_titel':   'Set password',
        'einladung_sub':     'Please set a password for your account.',
        'einladung_pw':      'Password',
        'einladung_pw2':     'Confirm password',
        'einladung_btn':     'Activate account',
        'einladung_abgelaufen': 'This invitation link has expired or is invalid.',

        # NDA Modal
        'nda_titel':         'Confidentiality Agreement & Bidding Terms',
        'nda_sub':           'Required reading before property access · cannot be closed without confirmation',
        'nda_scroll_hint':   '↓ Please read completely to continue',
        'nda_check1':        'I confirm that I have fully read and understood the bidding terms.',
        'nda_check2':        'I commit to confidentiality as per the NDA above.',
        'nda_check3':        'I understand that submitted bids are legally binding.',
        'nda_btn':           'Confirm & view property',
        'nda_note':          'This confirmation is logged with timestamp and IP address',

        # Bieter Dashboard
        'bieter_titel':      'Active Procedures',
        'meine_verfahren':   'My Procedures',
        'hoechstgebot':      'Highest bid',
        'startpreis':        'Starting price',
        'endet_in':          'Procedure ends in',
        'dokumente':         'Documents',
        'download':          '↓ Download',
        'gebot_label':       'Place a bid',
        'gebot_hint':        'Minimum bid: above current highest bid',
        'gebot_check':       'My bid is legally binding.',
        'gebot_btn':         'Submit bid',
        'nda_ausstehend':    'NDA required',
        'noch_kein_gebot':   'No bid yet',
        'tage':              'Days',
        'stunden':           'Hrs',
        'minuten':           'Min',
        'sekunden':          'Sec',

        # Costs
        'nebenkosten':       'Additional costs',
        'maklerprovision':   'Agent commission',
        'notarkosten':       'Notary fees',
        'grunderwerbssteuer': 'Property transfer tax',
        'grundbucheintragung': 'Land registry fee',
        'gesamt_nebenkosten': 'Estimated additional costs',

        # Admin
        'admin_dashboard':   'Dashboard',
        'admin_objekte':     'Properties',
        'admin_bieter':      'Bidders',
        'admin_anfragen':    'Requests',
        'admin_nda':         'NDA Records',
        'admin_einladungen': 'Invitations',
        'admin_nutzer':      'Users',
        'admin_audit':       'Audit Log',
        'admin_einstellungen': 'Settings',
        'bestaetigen':       'Approve',
        'ablehnen':          'Decline',
        'einladen':          'Invite',
        'neu_anlegen':       'Create new',
        'speichern':         'Save',
        'loeschen':          'Delete',
        'exportieren':       'Export',
        'alle_ansehen':      'View all',
        'pdf_export':        'PDF Export',
        'csv_export':        'CSV Export',

        # Status
        'aktiv':             'Active',
        'ausstehend':        'Pending',
        'abgelehnt':         'Declined',
        'endet_bald':        'Ending soon',
        'vorbereitung':      'Preparation',
        'beendet':           'Closed',
        'bestaetigt':        '✔ Confirmed',
        'nda_bestaetigt':    '✔ Confirmed',
        'nda_ausstehend_status': '⏳ Pending',

        # Admin Metrics
        'aktive_objekte':    'Active Properties',
        'aktive_bieter':     'Active Bidders',
        'offene_anfragen':   'Open Requests',
        'nda_bestaetigt_ratio': 'NDA Confirmed',
        'aktive_verfahren':  'Active Procedures',
        'offene_anfragen_card': 'Open Requests',

        # Admin Property form
        'geschaeftsbeziehung': 'Business type',
        'titel_immobilie':   'Property title',
        'objektnummer':      'Property number',
        'flaeche_m2':        'Area in m²',
        'strasse':           'Street',
        'plz':               'Postal code',
        'ort':               'City',
        'land':              'Country',
        'beschreibung':      'Description',
        'link_detail':       'Link to detailed description',
        'link_3d':           'Link to 3D tour',
        'beginn':            'Start',
        'ende':              'End',
        'startpreis_label':  'Starting price (€)',
        'zielpreis_label':   'Target price internal (€)',
        'sofortkauf':        'Buy now option',
        'sofortkauf_preis':  'Buy now price (€)',
        'provision_label':   'Agent commission (%)',
        'notar_label':       'Notary fees (%)',
        'grunderwerb_label': 'Property transfer tax (%)',
        'gb_label':          'Land registry fee (%)',
        'nebenkosten_ausbl': 'Hide additional costs',
        'gb_nebenkosten_ausbl': 'Hide land registry costs',
        'zusatzvereinbarungen': 'Additional agreements',
        'binding_ausbl':     'Hide binding confirmation',
        'angebotsliste_ausbl': 'Hide offer list',
        'jetzt':             'Now',
        'in_1_woche':        '+1 week',
        'in_2_wochen':       '+2 weeks',
        'in_3_wochen':       '+3 weeks',

        # FAQ
        'faq_titel':         'Frequently Asked Questions',
        'wie_funktioniert_q': 'How does the bidding procedure work?',
        'wie_funktioniert_a': 'A structured sales process for residential investment properties: interested parties submit binding bids. Only the current highest bid is visible – no names, no bidder count.',
        'zugang_q':          'How do I get access?',
        'zugang_a':          'Access is by invitation only or after review by the admin. Once approved, NDA and bidding terms must be confirmed.',
        'bindend_q':         'Are bids legally binding?',
        'bindend_a':         'Yes. All bids are legally binding. Purchase agreement and escrow services are handled by RA Mag. Werner Maierhofer.',
        'wer_q':             'Who is behind the platform?',
        'wer_a':             'Bieterverfahren Wien is a service of RA Mag. Werner Maierhofer, specialist in residential investment property transactions.',

        # Footer
        'footer_copyright':  '© 2025 Bieterverfahren Wien',
        'footer_link':       'bieterverfahrenwien.at ↗',

        # 2FA
        '2fa_titel':         'Set up two-factor authentication',
        '2fa_anleitung':     'Scan the QR code with Google Authenticator or a compatible app.',
        '2fa_code':          '6-digit code',
        '2fa_btn':           'Activate 2FA',
        '2fa_verify_titel':  'Two-factor authentication',
        '2fa_verify_sub':    'Please enter the code from your authenticator app.',
        '2fa_verify_btn':    'Confirm code',

        # Error messages
        'fehler_login':      'Incorrect email or password.',
        'fehler_2fa':        'Invalid code. Please try again.',
        'fehler_upload':     'File type not allowed or too large (max. 20 MB).',
        'fehler_gebot':      'Your bid must be above the current highest bid.',
        'fehler_nda':        'Please confirm all terms.',
        'erfolg_gebot':      'Your bid has been successfully submitted.',
        'erfolg_nda':        'NDA confirmed. You can now view the property.',
    }
}


def t(key, lang=None, **kwargs):
    """Übersetzungs-Helper – in Jinja2 als globale Funktion registriert."""
    if lang is None:
        lang = session.get('lang', 'de')
    text = T.get(lang, T['de']).get(key, key)
    return text.format(**kwargs) if kwargs else text


def current_lang():
    """Gibt die aktuelle Sprache zurück."""
    return session.get('lang', 'de')
