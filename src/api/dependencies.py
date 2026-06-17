"""
Shared dependencies for API routes.
"""

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..db.logging import get_db
from ..tasks.celery_app import app as celery_app
from ..inference.predictor import get_predictor


async def get_celery_app():
    """Get Celery app instance."""
    return celery_app


def get_predictor_instance():
    """Get model predictor instance."""
    predictor = get_predictor()
    if not predictor.is_loaded():
        predictor.load_model()
    return predictor


def get_db_session():
    """Get database session."""
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()