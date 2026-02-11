# Gemini Context: ACM Support Documentation Generator

This project is a specialized ETL (Extract, Transform, Load) pipeline for documentation. It aggregates technical documentation from various sources (Git repositories, web URLs, local files), cleans and formats it into a standardized Markdown format, and outputs a flat dataset optimized for ingestion by Large Language Models (specifically Google's NotebookLM and RAG systems).

## Project Architecture

### Core Components
*   **Orchestrator (`Makefile`)**: The central entry point. It manages dependencies, environment setup, and the execution order of the processing pipeline.
*   **Processors (`scripts/*.py`)**: Python scripts that handle specific data transformations:
    *   `convert_adoc_to_md.py`: Converts AsciiDoc to Markdown via DocBook, applying cleaning rules.
    *   `clean_docbook.py`: Manipulates XML to strip navigation, flatten tables to lists, and remove images.
    *   `process_crd.py`: Parses Kubernetes CRD YAMLs into human-readable Markdown references.
    *   `assemble_ocp_doc.py`: Aggregates split OpenShift documentation files into a single coherent document.
*   **Configuration (`config/`)**: Version-specific YAML files defining external resources to fetch.

### Directory Structure
*   **`config/`**: Contains `extra_docs_<version>.yaml` files listing external URLs (Markdown or CRDs) to include.
*   **`docs/`**: Meta-documentation, including the `notebooklm_persona.md` which defines the AI agent's behavior.
*   **`extra_local/`**: Version-specific manual documentation (e.g., internal notes for a specific release).
*   **`notebooklm_export/`**: **Artifact Directory**. This is where all generated Markdown files are output.
*   **`scripts/`**: The Python and Shell scripts powering the transformation logic.
*   **`static/`**: Global manual documentation applicable to all versions (e.g., general PromQL queries).
*   **`tmp/`**: Temporary working directory for cloning repositories (ignored by Git).

## Development & Usage

### Prerequisites
*   **System Tools**: `git`, `make`, `asciidoctor`, `pandoc`.
*   **Python**: Python 3.11+ managed by `uv`.

### Key Commands
*   **Setup**: Initialize the environment.
    ```bash
    make setup
    ```
*   **Full Build**: Generate documentation for a specific version.
    ```bash
    make all ACM_VERSION=2.15 OCP_VERSION=4.20
    ```
*   **Clean**: Remove build artifacts and temporary files.
    ```bash
    make clean
    ```

### common Tasks
1.  **Adding a New External Doc**:
    *   Edit `config/extra_docs_<version>.yaml`.
    *   Add a new entry with `name` and `url`. Set `type: crd` if it's a Kubernetes CRD.
2.  **Adding an Internal Note**:
    *   Place the Markdown file in `extra_local/<version>/`.
    *   Run `make copy-local` (or `make all`) to include it in the export.
3.  **Updating the Agent Persona**:
    *   Modify `docs/notebooklm_persona.md`.
    *   This file is not used in the build but serves as the source of truth for configuring the NotebookLM instance.

## Technical Constraints & Conventions
*   **Flat Output**: The pipeline intentionally flattens the directory structure. All files in `notebooklm_export/` are prefixed (e.g., `acm_2.15_...`, `ocp_4.20_...`) to ensure uniqueness and provide context to the LLM.
*   **Content Cleaning**: The pipeline aggressively removes non-textual elements (images, nav bars) to maximize the "information density" for the LLM context window. Tables are converted to lists to prevent formatting issues in the model's understanding.
*   **Source Priority**: The AI persona is instructed to prioritize `extra_local/` and `static/` content over official docs (`acm_*`, `ocp_*`) to handle known bugs or internal workarounds.
