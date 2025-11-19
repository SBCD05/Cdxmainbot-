FROM python:3.11-slim

WORKDIR /app

# Install system dependencies required for pandas/numpy
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    libssl-dev \
    libffi-dev \
    wget \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Install python requirements
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r /app/requirements.txt

# --- Install pandas_ta manually using ZIP (works on Fly.io) ---
RUN wget https://codeload.github.com/twopirllc/pandas-ta/zip/refs/heads/main -O pandas_ta.zip \
    && unzip pandas_ta.zip \
    && pip install ./pandas-ta-main \
    && rm -rf pandas_ta.zip pandas-ta-main

# Copy project files
COPY . /app

ENV PYTHONUNBUFFERED=1

CMD ["python", "Mainrunbots.py"]