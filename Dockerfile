FROM python:3.11-slim

WORKDIR /app

# Install system dependencies required for pandas, numpy, TA libs
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    libssl-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy project files
COPY . /app

ENV PYTHONUNBUFFERED=1

# Run the main bot
CMD ["python", "Mainrunbots.py"]