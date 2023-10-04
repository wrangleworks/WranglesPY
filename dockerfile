FROM python:3.10.13-slim-bookworm AS compile-image

# Copy package
COPY . /pkg

# Install compile requirements
RUN apt-get update \
    && apt-get install -y build-essential gcc \
    gfortran python3-dev \
    --no-install-recommends

# Create a virtual env
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install package + dependencies
RUN pip install --no-cache-dir wheel
# Special install for numpy to reduce size
RUN CFLAGS="-g0 -Wl,--strip-all" pip install --no-cache-dir --compile --global-option=build_ext numpy==1.24.3
# Regular install (without cache) for everything else
RUN pip install --no-cache-dir /pkg

# Botocore contains lots of definitions for all AWS services. We are only using S3. Remove all other files to save space
RUN cd /opt/venv/lib/python3.10/site-packages/botocore/data && cp -r s3 _retry.json endpoints.json partitions.json sdk-default-configuration.json /tmp/
RUN rm -r /opt/venv/lib/python3.10/site-packages/botocore/data/*
RUN cp -r /tmp/s3 /tmp/_retry.json /tmp/endpoints.json /tmp/partitions.json /tmp/sdk-default-configuration.json /opt/venv/lib/python3.10/site-packages/botocore/data

# Pandas contains a lot of unnecessary test data that we won't use
RUN rm -r /opt/venv/lib/python3.10/site-packages/pandas/tests/*

# Create build image
FROM python:3.10.13-slim-bookworm AS build-image
COPY --from=compile-image /opt/venv /opt/venv

LABEL maintainer="WrangleWorks"
ENV PATH="/opt/venv/bin:$PATH"

RUN mkdir /app
COPY main.py /app/
WORKDIR /app/

CMD python main.py
