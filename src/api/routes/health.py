from fastapi import APIRouter, status
from datetime import datetime
import logging
from sqlalchemy import text
from src.db.logging import SessionLocal
from src.tasks.celery_app import app as celery_app
import redis

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/health", tags=["health"])


@router.get("", status_code=status.HTTP_200_OK)
async def health_check():
    """General health check."""
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "forex-trading-bot"
    }


@router.get("/db", status_code=status.HTTP_200_OK)
async def health_check_db():
    """Check database connectivity."""
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        return {
            "status": "ok",
            "service": "postgresql",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "error",
            "service": "postgresql",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }, status.HTTP_503_SERVICE_UNAVAILABLE


@router.get("/redis", status_code=status.HTTP_200_OK)
async def health_check_redis():
    """Check Redis connectivity."""
    try:
        from src.config import REDIS_URL
        r = redis.from_url(REDIS_URL)
        r.ping()
        return {
            "status": "ok",
            "service": "redis",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return {
            "status": "error",
            "service": "redis",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }, status.HTTP_503_SERVICE_UNAVAILABLE


@router.get("/celery", status_code=status.HTTP_200_OK)
async def health_check_celery():
    """Check Celery worker status."""
    try:
        inspect = celery_app.control.inspect()
        stats = inspect.stats()

        if stats is None:
            return {
                "status": "error",
                "service": "celery",
                "error": "No workers found",
                "timestamp": datetime.utcnow().isoformat()
            }, status.HTTP_503_SERVICE_UNAVAILABLE

        return {
            "status": "ok",
            "service": "celery",
            "workers": len(stats),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Celery health check failed: {e}")
        return {
            "status": "error",
            "service": "celery",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }, status.HTTP_503_SERVICE_UNAVAILABLE
