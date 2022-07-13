FROM python:3.10.4-slim-buster AS compile-image

# Copy package
COPY . /pkg

RUN apt-get update \
    && apt-get install -y build-essential gcc gfortran python3-dev --no-install-recommends

# Create a virtual env
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install package + dependencies
# Special install for the largest packages to reduce size
RUN CFLAGS="-g0 -Wl,--strip-all" pip install --no-cache-dir --compile --global-option=build_ext pandas numpy sqlalchemy
# Regular install (wihtout cache) for everything else
RUN pip install --no-cache-dir /pkg


# Create build image
FROM python:3.10.4-slim-buster AS build-image
COPY --from=compile-image /opt/venv /opt/venv

LABEL maintainer="WrangleWorks"
ENV PATH="/opt/venv/bin:$PATH"

RUN mkdir /app
COPY main.py /app/
WORKDIR /app/

CMD python main.py