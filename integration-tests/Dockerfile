FROM python:3.9-slim

WORKDIR /app
ARG GEMFURY_DOWNLOAD_KEY

ADD requirements.txt .

RUN apt-get update \
    && apt-get install -y wait-for-it \
    && pip config --user set install.extra-index-url "https://pypi.fury.io/${GEMFURY_DOWNLOAD_KEY}/sensynehealth/" \
    && pip install -r requirements.txt

ADD . .

CMD ["behave", "--no-capture"]
