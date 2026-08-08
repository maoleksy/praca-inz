# services/scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler
from scrapers.answear.monitor import monitor_from_db

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(monitor_from_db, "interval", seconds=30)
    scheduler.start()
    return scheduler
