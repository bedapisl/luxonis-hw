FROM python:3.9.6
#
#RUN pip install pipenv==2022.10.12
#
#COPY Aptfile Aptfile
#RUN apt-get update \
#    && xargs -a Aptfile apt-get install -y
#
#COPY Pipfile Pipfile
#COPY Pipfile.lock Pipfile.lock

COPY requirements.txt requirements.txt

RUN pip3 install -r requirements.txt

#RUN pipenv install --system

## Certificates that includes one for Nexus
#ENV REQUESTS_CA_BUNDLE /certs/ca-certificates.crt
#COPY ca-certificates.crt /certs/ca-certificates.crt

WORKDIR /app
