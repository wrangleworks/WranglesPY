FROM python:3.10.4-slim-buster

LABEL maintainer="WrangleWorks"

COPY . /pkg

RUN python -m pip install --upgrade pip && \
    pip install /pkg
    
RUN mkdir /app

COPY main.py /app/

WORKDIR /app/

CMD python main.py