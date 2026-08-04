"""Background scheduler for email reminders."""

import threading
import time

_started = False


def start_reminder_scheduler(app):
    global _started
    if _started:
        return
    _started = True

    def loop():
        while True:
            interval = 15
            try:
                with app.app_context():
                    from reminders_service import get_email_settings, process_due_reminders

                    settings = get_email_settings()
                    interval = max(5, int(settings.get("check_interval_minutes") or 15))
                    if settings.get("enabled"):
                        process_due_reminders()
            except Exception as exc:
                print(f"PowerFlow reminder scheduler: {exc}")
            time.sleep(interval * 60)

    threading.Thread(target=loop, daemon=True, name="powerflow-reminders").start()
