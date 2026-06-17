#!/bin/bash

# Start FastAPI server
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload