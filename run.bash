#!/bin/bash
uvicorn fastapi_blog.app:app --host 0.0.0.0 --port 8080
