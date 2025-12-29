from __future__ import annotations

from trade_guardian.workers.celery_app import app


@app.task(name="workers.ping")
def ping() -> str:
    return "pong"


