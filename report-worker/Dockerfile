# report-worker/Dockerfile

# 1. Base image
FROM python:3.11-slim-bullseye

# 2. Set working directory
WORKDIR /app

# 3. System dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        curl \
    && rm -rf /var/lib/apt/lists/*

# 4. Install Python dependencies
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy application code
COPY . .

# 6. Environment variables
ENV PORT=8080
ENV PYTHONUNBUFFERED=1

# 7. Expose port
EXPOSE 8080

# 8. Start the service with Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
