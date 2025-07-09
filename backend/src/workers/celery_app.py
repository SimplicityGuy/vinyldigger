from celery import Celery

from src.core.config import settings

celery_app = Celery(
    "vinyldigger",
    broker=str(settings.celery_broker_url),
    backend=str(settings.celery_result_backend),
    include=["src.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)
