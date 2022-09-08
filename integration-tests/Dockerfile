FROM python:3.9-slim

WORKDIR /app

ADD requirements.txt .

RUN apt-get update \
    && apt-get install -y wait-for-it \
    && pip install -r requirements.txt

ADD . .

CMD ["behave", "--no-capture"]
