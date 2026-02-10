# ACM Support Documentation Generator

This project generates a consolidated, flat set of Markdown documentation for Red Hat Advanced Cluster Management (ACM) and OpenShift, specifically optimized for ingestion into tools like **NotebookLM** and RAG systems. It combines official documentation, custom runbooks, product-specific Markdown files, and OpenShift monitoring docs into a single directory.

## Features

- **Official Docs (RHACM)**: Automatically clones and processes the official RHACM documentation repository.
- **OpenShift Docs (Monitoring)**: Fetches and consolidates OpenShift monitoring documentation into a single, structured file.
- **Extra Docs**: Fetches additional Markdown files (runbooks, READMEs) and CRDs from any URL (with special handling for GitHub).
- **CRD Processing**: Automatically converts Kubernetes CRDs into LLM-friendly Markdown references.
- **DocBook Cleaning**: Strips images, navigation lists, and converts complex tables into prose.
- **HTML Cleaning**: Removes raw HTML tags to ensure clean Markdown output.
- **Flat Output**: Generates all files in a single `notebooklm_export/` directory with identifiable prefixes.
- **Versioned Configuration**: Supports different sets of extra documents per ACM/OCP version.

## Prerequisites

Ensure you have the following installed on your system:

- **Git**: For cloning repositories.
- **Python 3.11+**: For processing scripts.
- **[uv](https://github.com/astral-sh/uv)**: For Python dependency management.
- **Asciidoctor**: For converting `.adoc` to DocBook XML (`brew install asciidoctor`).
- **Pandoc**: For converting DocBook XML to Markdown (`brew install pandoc`).

## Setup

Initialize the Python virtual environment and install dependencies:

```bash
make setup
```

## Usage

### 1. Configure Extra Documents (URLs)

Create a YAML file in the `config/` directory for your target ACM version, e.g., `config/extra_docs_2.15.yaml`.

**Supported Types:**
- `markdown` (default): Standard Markdown files. Images are stripped/replaced with alt text.
- `crd`: Kubernetes Custom Resource Definition YAMLs. Converted to flattened Markdown references.

**Example:**
```yaml
- name: "Observability Troubleshooting"
  url: "https://github.com/stolostron/multicluster-observability-operator/blob/main/docs/troubleshooting/troubleshooting.md"
- name: "MultiClusterObservability CRD"
  url: "https://github.com/stolostron/multicluster-observability-operator/blob/main/operators/multiclusterobservability/bundle/manifests/observability.open-cluster-management.io_multiclusterobservabilities.yaml"
  type: "crd"
```

### 2. Add Local Documents (Manual Exports)

- **Global Documents (`static/`)**: Place files that should be included in *all* versions (e.g., generic PromQL queries).
  - Example: `static/useful_promql_queries.md` -> `notebooklm_export/static_useful_promql_queries.md`
- **Version-Specific Documents (`extra_local/<version>/`)**: Place files for a specific version (e.g., manual Google Doc exports).
  - Example: `extra_local/2.15/my_doc.md` -> `notebooklm_export/local_2.15_my_doc.md`

### 3. Generate Documentation

Run the full generation process. You can specify the ACM and OCP versions:

```bash
make all ACM_VERSION=2.15 OCP_VERSION=4.20
```

**Output:** All generated files will be in the **`notebooklm_export/`** directory.

- **RHACM Docs**: `acm_<version>_<topic>_main.md`
- **OpenShift Docs**: `ocp_<version>_monitoring.md`
- **Extra Docs**: `extra_<version>_<name>.md`
- **Local Docs**: `local_<version>_<name>.md`
- **Static Docs**: `static_<name>.md`

## Available Make Targets

- `make setup`: Initializes the `uv` environment.
- `make all`: Runs the full pipeline (fetch official, fetch OCP, process all, fetch extra, copy local).
- `make fetch-official`: Clones the official RHACM docs to `tmp/rhacm-docs`.
- `make process-official`: Converts RHACM docs to flat Markdown files.
- `make fetch-ocp`: Clones OpenShift docs to `tmp/openshift-docs`.
- `make process-ocp`: Assembles OpenShift monitoring docs into a single file.
- `make fetch-extra`: Fetches documents listed in the YAML config.
- `make copy-local`: Copies static and local documents to the export directory.
- `make clean`: Removes generated content, repo clones, and the `.venv`.

## Project Structure

- `config/`: Version-specific YAML configurations.
- `notebooklm_export/`: **Final output directory**.
- `static/`: Global manual documents.
- `extra_local/`: Version-specific manual documents.
- `scripts/`: Processing scripts (`assemble_ocp_doc.py`, `convert_adoc_to_md.py`, `fetch_*.sh`).
- `tmp/`: Temporary storage for cloned repositories.