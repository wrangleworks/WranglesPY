#!/bin/sh
set -eu

# Run the credential-safe local suite against the package already installed in
# the image. Work from a disposable copy so the checked-out source package
# cannot shadow that installation.
workspace=${1:-/workspace}
test_root=$(mktemp -d /tmp/wrangles-container-tests.XXXXXX)
trap 'rm -rf "$test_root"' EXIT

cp -R "$workspace"/. "$test_root"/
rm -rf "$test_root/.git" "$test_root/.test-local" "$test_root/wrangles"

unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN
unset GEMINI_API_KEY HUGGINGFACE_TOKEN OPENAI_API_KEY SERPAPI_API_KEY
unset WRANGLES_PASSWORD WRANGLES_USER

cd "$test_root"
python -m pip install \
    --no-cache-dir \
    --constraint constraints/container-python313.txt \
    --requirement requirements-full.txt \
    pytest==9.0.2 pytest-mock==3.15.1
python -m pytest \
    -c pytest-local.ini \
    --basetemp=/tmp/wrangles-container-pytest
