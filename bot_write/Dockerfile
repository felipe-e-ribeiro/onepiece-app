FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
COPY app.py .
RUN useradd app ; pip install --no-cache-dir -r requirements.txt ;  chown app:app -R /app
USER app
CMD ["python", "/app/app.py"]