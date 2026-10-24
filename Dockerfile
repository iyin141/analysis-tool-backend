FROM python:3.13-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir \
    --default-timeout=120 \
    --retries 5 \
    -r requirements.txt

# Copy backend application and committed data
COPY app /app/app

EXPOSE 2847

ENV PYTHONUNBUFFERED=1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "2847"]