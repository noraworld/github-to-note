FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    chromium-driver \
    ca-certificates \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install --no-cache-dir selenium requests python-dotenv

COPY note_api /app/note_api
COPY main.py /app/main.py

ENV CHROME_BINARY=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

ENTRYPOINT ["python", "/app/main.py"]
