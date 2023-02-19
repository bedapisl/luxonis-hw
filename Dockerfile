FROM python:3.9.6

COPY requirements.txt requirements.txt

RUN pip3 install -r requirements.txt

WORKDIR /app
