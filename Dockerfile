FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc g++ libssl-dev libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first for better cache usage
COPY requirements.txt .

# Upgrade pip and install python dependencies
RUN pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt

# Copy rest of application files
COPY . .

ENV PYTHONUNBUFFERED=1

# Main entrypoint to run your bot
CMD ["python", "Mainrunbots.py"]