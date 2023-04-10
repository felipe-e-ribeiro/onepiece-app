FROM alpine:3.14
RUN apk add python3 py3-pip && apk add --virtual build-deps gcc python3-dev musl-dev && apk add --no-cache mariadb-dev
COPY . /app
WORKDIR /app
RUN pip3 install -r requirements.txt
RUN apk del build-deps
ENV MYSQL_HOST=$MYSQL_HOST
ENV MYSQL_USER=$MYSQL_USER
ENV MYSQL_PASSWORD=$MYSQL_PASSWORD
ENV MYSQL_DB=$MYSQL_DB
ENTRYPOINT ["python3"]
CMD ["-m", "flask", "run" ]
