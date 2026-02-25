FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY . .

# Expose skill directory (mounted via docker-compose)
RUN mkdir -p /skill

EXPOSE 8080

CMD ["python", "app.py"]
