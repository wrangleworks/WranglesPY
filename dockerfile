# syntax=docker/dockerfile:1

FROM python:3.13-slim-bookworm AS dependency-image

# Copy package
COPY . /pkg

# Create a virtual env
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install the package with the CI test-image data-stack constraint. Every
# dependency must resolve to a wheel because the image has no compiler.
# pyarrow is an optional (requirements-full.txt) dependency of the package
# itself, but this image's smoke test exercises it directly to validate
# NumPy/Pandas/PyArrow wheel interop, so it's installed explicitly here.
RUN python -m pip install \
    --no-cache-dir \
    --only-binary=:all: \
    --constraint /pkg/constraints/test-container-python313.txt \
    /pkg packaging pyarrow

# Retain only the Botocore data used by the S3 connector and remove Pandas test
# data. Resolve installed-package locations instead of embedding a Python minor.
RUN python - <<'PY'
from pathlib import Path
import shutil

import botocore
import pandas

botocore_data = Path(botocore.__file__).resolve().parent / "data"
keep = {
    "s3",
    "_retry.json",
    "endpoints.json",
    "partitions.json",
    "sdk-default-configuration.json",
}
for path in botocore_data.iterdir():
    if path.name in keep:
        continue
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()

pandas_tests = Path(pandas.__file__).resolve().parent / "tests"
if pandas_tests.exists():
    shutil.rmtree(pandas_tests)
PY

# Fail the build before the runtime stage if versions, metadata, package-data
# trimming, imports, or the credential-free data/S3 checks are incorrect.
RUN python -m pip check \
    && python /pkg/scripts/container_smoke.py

# Create build image
FROM python:3.13-slim-bookworm AS build-image
COPY --from=dependency-image /opt/venv /opt/venv

LABEL maintainer="WrangleWorks"
ENV PATH="/opt/venv/bin:$PATH"

RUN mkdir /app
COPY main.py /app/
WORKDIR /app/

CMD python main.py
