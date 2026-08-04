FROM python:3.11-slim

# 1. Install tzdata and explicitly link the Manila timezone file to /etc/localtime
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y tzdata && \
    ln -sf /usr/share/zoneinfo/Asia/Manila /etc/localtime && \
    echo "Asia/Manila" > /etc/timezone && \
    rm -rf /var/lib/apt/lists/*

# 2. Force environment variable for Python timezone
ENV TZ=Asia/Manila

WORKDIR /app

# 3. Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy application files
COPY . .

# 5. Dynamically bind Waitress to the PORT environment variable set by Coolify (defaults to 5000 if not set)
CMD ["sh", "-c", "waitress-serve --host=0.0.0.0 --port=${PORT:-5000} app:app"]