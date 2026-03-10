FROM python:3.12-slim

# Install ffmpeg (required by pydub for audio conversion)
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ app/
COPY web/ web/
COPY web_server.py .

EXPOSE 8000

CMD ["gunicorn", "--bind=0.0.0.0:8000", "--timeout=120", "--workers=2", "web_server:app"]
