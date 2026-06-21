# Reproducible scrape environment. Build:  docker build -t locus7-kb-scraper .
# Run:    docker run --rm -v "$PWD/data:/app/data" locus7-kb-scraper scrape --source kubernetes
FROM python:3.12-slim

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
ENV PYTHONPATH=/app/src
ENTRYPOINT ["python", "-m", "kbscraper"]
CMD ["list"]
