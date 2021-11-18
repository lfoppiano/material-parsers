FROM python:3.7.11-slim-buster

ENV LANG C.UTF-8

RUN apt-get update && \
    apt-get -y --no-install-recommends install \
    git \
    python3-venv python3-dev build-essential gcc\
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*


RUN mkdir -p /opt/service/venv && \
    mkdir -p /opt/service/resources   

WORKDIR /opt/service

# Copy resources 
COPY requirements.txt .
COPY resources/config.json resources
COPY resources/data /opt/service/resources/data


ENV VIRTUAL_ENV=/opt/service/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN python3 -m pip install pip --upgrade
RUN python3 -m pip install -r ./requirements.txt
RUN python3 -m spacy download en_core_web_sm

# extract version 
COPY .git ./.git
RUN git rev-parse --short HEAD > /opt/service/resources/version.txt
RUN rm -rf ./.git

# Copy code 
COPY grobid_superconductors /opt/service/grobid_superconductors
#COPY __main__.py /opt/service

EXPOSE 8080

CMD ["python3", "-m", "grobid_superconductors", "--config", "resources/config.json"]
