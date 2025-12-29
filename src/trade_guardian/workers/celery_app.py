from __future__ import annotations

from celery import Celery

from trade_guardian.utils.config import get_settings

settings = get_settings()

app = Celery(
    "trade_guardian",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

app.conf.update(
    task_default_queue="default",
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_time_limit=60,
)


