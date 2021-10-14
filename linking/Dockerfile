FROM python:3.7.11-slim-buster

ENV LANG C.UTF-8

RUN apt-get update && \
    apt-get -y --no-install-recommends install \
    git \
    python3-venv python3-dev build-essential gcc\
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*


RUN mkdir -p /opt/linking/venv

WORKDIR /opt/linking

COPY requirements.txt .
COPY config.json .
COPY *.py .

ENV VIRTUAL_ENV=/opt/linking/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN python3 -m pip install pip --upgrade
RUN python3 -m pip install -r ./requirements.txt
RUN python3 -m spacy download en_core_web_sm

EXPOSE 8080

CMD ["python3", "/opt/linking/service.py", "-config config.json"]