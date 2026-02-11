# ACM Support Documentation Generator

Generates a consolidated, flat set of Markdown documentation for Red Hat Advanced Cluster Management (ACM) and OpenShift, optimized for RAG systems and **NotebookLM**.

## Quick Start

### Prerequisites
- **Tools**: Make, Git, Python 3.11+, [uv](https://github.com/astral-sh/uv).
- **Converters**: Asciidoctor & Pandoc (`brew install asciidoctor pandoc`).

### Build
1.  **Setup**: `make setup`
2.  **Generate**: `make all ACM_VERSION=2.15 OCP_VERSION=4.20`

**Output**: All files are generated in `notebooklm_export/`.

## Key Capabilities

- **Unified Format**: Consolidates RHACM (Asciidoc), OpenShift (GitHub), and custom resources into a flat, searchable Markdown directory.
- **Intelligent Cleaning**: 
    - **Noise Reduction**: Strips UI fluff, navigation bars, and conversion artifacts (e.g., empty `div` tags).
    - **Navigation & TOCs**: Removes Tables of Contents and "See also" link lists to keep the focus on actionable content.
    - **Table Flattening**: Transforms complex documentation tables into simple, LLM-readable bulleted lists.
    - **Link & Image Stripping**: Flattens hyperlinks to plain text and removes diagrams to minimize token noise.
    - **Structural Cleanup**: Automatically prunes empty sections and redundant headers.
- **CRD Flattening**: Transforms complex Kubernetes Custom Resource Definitions (YAML) into structured Markdown references for better model comprehension.
- **Automated Fetching**: Handles branch-aware GitHub cloning for official docs and version-specific configuration for extra resources.

## Configuration

### 1. Extra Documents (URLs)
Define external resources in `config/extra_docs_<version>.yaml`.

```yaml
- name: "Observability Troubleshooting"
  url: "https://github.com/.../troubleshooting.md"
- name: "MultiClusterObservability CRD"
  url: "https://github.com/.../crd.yaml"
  type: "crd"
```

### 2. Manual Documents (Local)
- **Global**: `static/` -> `notebooklm_export/static_<name>.md` (e.g., generic PromQL).
- **Versioned**: `extra_local/<version>/` -> `notebooklm_export/local_<version>_<name>.md` (e.g., internal notes).

## Workflows

### Onboarding a New Version
1.  **Config**: Create `config/extra_docs_<new_version>.yaml`. Update URLs to the new release branch.
2.  **Local Docs**: Create `extra_local/<new_version>/` and populate with relevant internal notes.
    *   *Tip: Use "Copy as Markdown" in Google Docs. Manually remove image references.*
3.  **Build**: Run `make all ACM_VERSION=<new_version> OCP_VERSION=<ocp_version>`.

### Setting up NotebookLM
1.  **Create**: New notebook in [NotebookLM](https://notebooklm.google.com/).
2.  **Source**: Upload all `.md` files from `notebooklm_export/`.
3.  **Instruct**: Create a "Saved Note" titled "Instructions" with content from `docs/notebooklm_persona.md`.
4.  **Share**: 
    - **Viewers**: announce-list@redhat.com (Access: "Chat only")
    - **Editors**: rhobs-dev@redhat.com
    - **Note**: Uncheck **"Notify People"** to avoid bulk emails.
    - **Intro**: Paste content from `docs/notebooklm_welcome.md`.

## Make Targets
- `make setup`: Init environment.
- `make all`: Run full pipeline.
- `make fetch-{official,ocp,extra}`: Fetch individual sources.
- `make process-{official,ocp}`: Process specific sources.
- `make clean`: Reset environment and cache.

## Project Structure
- `config/`: Version-specific YAML configurations.
- `notebooklm_export/`: **Final output directory**.
- `static/`: Global manual documents.
- `extra_local/`: Version-specific manual documents.
- `scripts/`: Processing scripts.
- `docs/`: Meta-documentation (Persona, Welcome message).
