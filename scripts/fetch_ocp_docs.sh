#!/bin/bash
set -eou pipefail

if [ -z "${1-}" ]; then
    echo "Error: OCP_VERSION argument is missing."
    echo "Usage: $0 <OCP_VERSION> <REPO_DIR>"
    exit 1
fi

if [ -z "${2-}" ]; then
    echo "Error: REPO_DIR argument is missing."
    echo "Usage: $0 <OCP_VERSION> <REPO_DIR>"
    exit 1
fi

OCP_VERSION=$1
REPO_DIR=$2

# Clean existing repo directory to ensure fresh clone
if [ -d "${REPO_DIR}" ]; then
    echo "Removing existing repository directory ${REPO_DIR}..."
    rm -rf "${REPO_DIR}"
fi

echo "Cloning OpenShift documentation for version ${OCP_VERSION}..."
# Using HTTPS for better portability. Branch format is usually 'enterprise-4.14' etc.
git clone --quiet --single-branch --branch "enterprise-${OCP_VERSION}" \
    https://github.com/openshift/openshift-docs.git "${REPO_DIR}"

echo "Done."
