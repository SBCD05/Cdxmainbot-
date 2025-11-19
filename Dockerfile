FROM python:3.11-slim

WORKDIR /app

# Install system dependencies required for pandas/numpy
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    libssl-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r /app/requirements.txt

# Install pandas_ta without git (zip method, supports Python 3.11+)
RUN pip install https://github.com/twopirllc/pandas-ta/archive/refs/heads/master.zip

COPY . /app

ENV PYTHONUNBUFFERED=1

CMD ["python", "Mainrunbots.py"]