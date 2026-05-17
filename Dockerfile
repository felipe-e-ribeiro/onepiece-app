FROM python:3.12-alpine

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY website/ ./website/

RUN mkdir -p output/static

ENV DRY_RUN=true

EXPOSE 8080

CMD sh -c "cd website && python volume_update.py && python -m http.server 8080 --directory /app/output"
