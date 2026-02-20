FROM python:3.12-alpine
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && adduser -D app

# Copia os arquivos como root, mas garante que o usuário app possa ler
COPY . .
RUN chown -R root:root /app && \
    chmod -R 555 /app && \
    chmod 444 /app/my_database.db

USER app
CMD ["flask", "run", "--host=0.0.0.0"]