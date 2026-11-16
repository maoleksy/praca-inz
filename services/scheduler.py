# services/scheduler.py
from apscheduler.events import EVENT_JOB_ERROR
from apscheduler.schedulers.background import BackgroundScheduler
from scrapers.answear.monitor import monitor_from_db
from scrapers.zalando.monitor import monitor_zalando
from scrapers.bestsecret.monitor import monitor_bestsecret
from scrapers.bestsecret.cart import check_cart_session
from services.notifier import send_error_alert


def _on_job_error(event):
    # Siatka bezpieczeństwa: monitor_from_db i monitor_zalando łapią własne
    # błędy i alertują same, ale to wyłapie wszystko, co by się jednak
    # wymknęło (np. błąd programistyczny poza try/except).
    send_error_alert(f"Scheduler job {event.job_id}", event.exception)


def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(monitor_from_db, "interval", seconds=30)
    # 300s -> 60s: poprzedni crash powodował głównie podwójny scheduler
    # (naprawiony), nie sam interwał. Jeśli w logach wrócą JSONDecodeError,
    # wróć na wyższą wartość (np. 180-300s).
    scheduler.add_job(monitor_zalando, "interval", seconds=60)
    scheduler.add_job(monitor_bestsecret, "interval", seconds=60)
    # Sesja konta do auto-ATC: martwy token ma wyjść od razu, nie przy restocku.
    scheduler.add_job(check_cart_session, "interval", minutes=30)
    scheduler.add_listener(_on_job_error, EVENT_JOB_ERROR)
    scheduler.start()
    return scheduler
