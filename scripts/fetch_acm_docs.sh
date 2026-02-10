#!/bin/bash
set -eou pipefail

if [ -z "${1-}" ]; then
    echo "Error: ACM_VERSION argument is missing."
    echo "Usage: $0 <ACM_VERSION> <REPO_DIR>"
    exit 1
fi

if [ -z "${2-}" ]; then
    echo "Error: REPO_DIR argument is missing."
    echo "Usage: $0 <ACM_VERSION> <REPO_DIR>"
    exit 1
fi

ACM_VERSION=$1
REPO_DIR=$2

# Clean existing repo directory to ensure fresh clone
if [ -d "${REPO_DIR}" ]; then
    echo "Removing existing repository directory ${REPO_DIR}..."
    rm -rf "${REPO_DIR}"
fi

echo "Cloning documentation for version ${ACM_VERSION}..."
# Clone specifically into the directory we expect (openshift-docs)
git clone --quiet --single-branch --branch "${ACM_VERSION}_prod" \
    https://github.com/stolostron/rhacm-docs.git "${REPO_DIR}"

echo "Done."
