FROM python:3.11-slim-bookworm

WORKDIR /app

# Install system build dependencies (needed for PyYAML on ARM architectures)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        libyaml-dev \
        python3-dev && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip list
# Expose port 8080
EXPOSE 8080

# Run the web server
CMD ["python", "server.py"]
