"""
Celery app configuration for forex trading bot.
"""

from celery import Celery
from ..config import REDIS_URL, CELERY_RESULT_BACKEND

app = Celery(
    "forex_trading_bot",
    broker=REDIS_URL,
    backend=CELERY_RESULT_BACKEND,
    include=[
        "src.tasks.inference_tasks",
        "src.tasks.retraining_tasks"
    ]
)

# Configure Celery
app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_default_queue="default",
    task_default_exchange="default",
    task_default_routing_key="default",
    task_routes={
        "src.tasks.inference_tasks.*": {
            "queue": "inference",
            "routing_key": "inference"
        },
        "src.tasks.retraining_tasks.*": {
            "queue": "retraining",
            "routing_key": "retraining"
        }
    }
)

if __name__ == "__main__":
    app.start()