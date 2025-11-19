FROM python:3.11-slim

WORKDIR /app

# Install system dependencies required for pandas/numpy
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    libssl-dev \
    libffi-dev \
    libatlas-base-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

ENV PYTHONUNBUFFERED=1

CMD ["python", "Mainrunbots.py"]
