import os
import shutil
import glob
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()


def datenbank_backup(app):
    """Tägliches Datenbank-Backup um 03:00 – letzte 30 behalten."""
    with app.app_context():
        from config import Config
        db_pfad = os.path.join(Config.BASE_DIR, 'database.db')
        backup_ordner = Config.BACKUP_FOLDER
        os.makedirs(backup_ordner, exist_ok=True)

        if not os.path.exists(db_pfad):
            print('[Scheduler] Keine Datenbank gefunden – Backup übersprungen.')
            return

        # Backup mit Zeitstempel
        zeitstempel = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_pfad = os.path.join(backup_ordner, f'database_{zeitstempel}.db')
        shutil.copy2(db_pfad, backup_pfad)
        print(f'[Scheduler] Backup erstellt: {backup_pfad}')

        # Alte Backups löschen (mehr als 30)
        backups = sorted(glob.glob(os.path.join(backup_ordner, 'database_*.db')))
        while len(backups) > 30:
            zu_loeschen = backups.pop(0)
            os.remove(zu_loeschen)
            print(f'[Scheduler] Altes Backup gelöscht: {zu_loeschen}')


def verfahren_pruefen(app):
    """Tägliche Prüfung um 08:00 – Start/Warn/Ende-Mails und Deaktivierung."""
    with app.app_context():
        from models import db, Objekt, ObjektZugang, User, AuditLog
        from mail import (mail_verfahren_startet, mail_verfahren_endet_bald,
                          mail_verfahren_beendet_bieter, mail_verfahren_beendet_admin)
        import json

        jetzt = datetime.utcnow()
        objekte = Objekt.query.filter_by(aktiv=True).all()

        for objekt in objekte:
            bieter_ids = [z.user_id for z in objekt.zugaenge]
            bieter = User.query.filter(User.id.in_(bieter_ids)).all() if bieter_ids else []

            # Verfahren startet heute?
            if objekt.beginn:
                diff_start = (objekt.beginn - jetzt).total_seconds()
                if 0 <= diff_start <= 86400:  # Innerhalb der nächsten 24h
                    print(f'[Scheduler] Verfahren startet: {objekt.titel}')
                    for b in bieter:
                        mail_verfahren_startet(b.email, b.name, objekt.titel,
                                               objekt.startpreis, objekt.ende)

            # Verfahren endet in 24h?
            if objekt.ende:
                diff_ende = (objekt.ende - jetzt).total_seconds()

                if 0 <= diff_ende <= 86400:
                    print(f'[Scheduler] Verfahren endet bald: {objekt.titel}')
                    hoechstgebot = objekt.hoechstgebot()
                    for b in bieter:
                        mail_verfahren_endet_bald(b.email, b.name, objekt.titel,
                                                  hoechstgebot, objekt.ende)

                # Verfahren beendet?
                elif diff_ende < 0:
                    print(f'[Scheduler] Verfahren beendet: {objekt.titel}')
                    hoechstgebot = objekt.hoechstgebot()

                    # Gewinner ermitteln
                    gewinner = None
                    if hoechstgebot:
                        from models import Gebot
                        gebot = Gebot.query.filter_by(objekt_id=objekt.id).order_by(
                            Gebot.betrag.desc()
                        ).first()
                        if gebot:
                            gewinner = gebot.bieter

                    # Bieter benachrichtigen
                    for b in bieter:
                        mail_verfahren_beendet_bieter(b.email, b.name, objekt.titel, hoechstgebot)

                    # Admin benachrichtigen (mit Gewinner-Details)
                    admin = User.query.filter_by(rolle='admin').first()
                    if admin:
                        anzahl_gebote = len(objekt.gebote)
                        mail_verfahren_beendet_admin(
                            admin.email,
                            objekt.titel,
                            hoechstgebot,
                            gewinner.name if gewinner else None,
                            gewinner.email if gewinner else None,
                            gewinner.firma if gewinner else None,
                            anzahl_gebote
                        )

                    # Objekt deaktivieren
                    objekt.aktiv = False

                    # Audit-Log
                    eintrag = AuditLog(
                        aktion='verfahren_beendet',
                        objekt_id=objekt.id,
                        details=json.dumps({
                            'gewinner': gewinner.email if gewinner else None,
                            'hoechstgebot': hoechstgebot
                        }, ensure_ascii=False)
                    )
                    db.session.add(eintrag)

        db.session.commit()
        print(f'[Scheduler] Verfahrensprüfung abgeschlossen ({len(objekte)} Objekte).')


def scheduler_starten(app):
    """Scheduler initialisieren und Jobs registrieren."""
    # Nicht doppelt starten (z.B. beim Flask-Reloader oder Import)
    if scheduler.running:
        return

    # Tägliches Backup um 03:00
    scheduler.add_job(
        func=datenbank_backup,
        args=[app],
        trigger='cron',
        hour=3,
        minute=0,
        id='datenbank_backup',
        replace_existing=True
    )

    # Tägliche Verfahrensprüfung um 08:00
    scheduler.add_job(
        func=verfahren_pruefen,
        args=[app],
        trigger='cron',
        hour=8,
        minute=0,
        id='verfahren_pruefen',
        replace_existing=True
    )

    scheduler.start()
    print('[Scheduler] Gestartet: Backup 03:00, Verfahrensprüfung 08:00')
