# Dockerfile — Atomic Habits (Production-Ready)
FROM python:3.12-slim

# 🔧 Install system dependencies (git + curl for reliability)
RUN apt-get update && apt-get install -y --no-install-recommends git curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY main.py .

# ✅ Now safe to use git+https://... and upgrade pip
RUN pip install --upgrade pip && \
    pip install "git+https://github.com/answerdotai/fasthtml.git" apscheduler

EXPOSE 8000
CMD ["python", "main.py"]
