FROM python:3
LABEL maintainer="dgaynullin@linagora.com"

WORKDIR /usr/src/app

# System dependencies
RUN apt-get update

# Python dependencies
COPY nlp_superservice/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt


RUN mkdir -p /var/log/supervisor/
RUN mkdir /usr/src/app/logs

# Modules
COPY nlp_superservice/nlp /usr/src/app/nlp
COPY nlp_superservice/supervisor /usr/src/app/supervisor
COPY nlp_superservice/docker-entrypoint.sh ./

COPY scripts/wait-for-it.sh ./
COPY scripts/healthcheck.sh ./

RUN chmod +x docker-entrypoint.sh wait-for-it.sh

ENV PYTHONPATH="${PYTHONPATH}:/usr/src/app/nlp"

#HEALTHCHECK CMD ./healthcheck.sh

HEALTHCHECK CMD curl localhost:80/healthcheck

EXPOSE 80

ENTRYPOINT ["./docker-entrypoint.sh"]

