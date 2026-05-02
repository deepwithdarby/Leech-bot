FROM aiogram/telegram-bot-api:latest

# Switch to root to install dependencies and manage file permissions
USER root

# Remove default entrypoint from the base image so we can run our custom script
ENTRYPOINT []

# Install Python, Aria2, and compilation tools required for tgcrypto/aiohttp
RUN apk add --no-cache \
    python3 \
    py3-pip \
    python3-dev \
    aria2 \
    bash \
    gcc \
    linux-headers \
    musl-dev

WORKDIR /app

# Create a Python virtual environment
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy and install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all remaining project files
COPY . .

# Create necessary directories and set loose permissions for tdlib and downloads
RUN mkdir -p /app/downloads /app/tdlib && \
    chmod 777 /app/downloads /app/tdlib && \
    chmod +x start.sh

# Expose port 7860 to satisfy Hugging Face Spaces requirements
EXPOSE 7860

CMD ["./start.sh"]
