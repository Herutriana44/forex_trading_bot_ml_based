#!/bin/bash

# Start Celery worker
celery -A src.tasks.celery_app worker --loglevel=info