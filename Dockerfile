FROM python:3.9-slim-bullseye

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
COPY delft /opt/service/delft

ENV VIRTUAL_ENV=/opt/service/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN python3 -m pip install pip --upgrade
RUN python3 -m pip install -r ./requirements.txt
RUN python3 -m spacy download en_core_web_sm
RUN python3 delft/preload_embeddings.py --registry delft/resources-registry.json

# extract version 
COPY .git ./.git
RUN git rev-parse --short HEAD > /opt/service/resources/version.txt
RUN rm -rf ./.git

# Copy code 
COPY material_parsers /opt/service/material_parsers
#COPY __main__.py /opt/service

EXPOSE 8080

CMD ["python3", "-m", "material_parsers", "--config", "resources/config.json"]
