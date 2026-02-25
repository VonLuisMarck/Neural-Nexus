FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# System deps for pycrypto / service-identity
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc libffi-dev libssl-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Port is overridable via env; default 5000
ENV PORT=5000
EXPOSE 5000

CMD ["python", "app.py"]
