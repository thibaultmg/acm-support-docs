ACM_VERSION ?= 2.15
OCP_VERSION ?= 4.20
DOCS_REPO_DIR = tmp/rhacm-docs
OCP_DOCS_REPO_DIR = tmp/openshift-docs
EXPORT_DIR = notebooklm_export
EXTRA_DOCS_CONFIG = config/extra_docs_$(ACM_VERSION).yaml

.PHONY: all fetch-official process-official fetch-ocp process-ocp fetch-extra copy-local clean clean-output check-deps setup

all: clean-output fetch-official process-official fetch-ocp process-ocp fetch-extra copy-local

check-deps:
	@which git > /dev/null || (echo "Error: git is not installed" && exit 1)
	@which uv > /dev/null || (echo "Error: uv is not installed" && exit 1)
	@which asciidoctor > /dev/null || (echo "Error: asciidoctor is not installed" && exit 1)
	@which pandoc > /dev/null || (echo "Error: pandoc is not installed" && exit 1)
	@echo "All dependencies check out."

setup: check-deps
	uv sync

fetch-official: check-deps
	@mkdir -p tmp
	./scripts/fetch_acm_docs.sh $(ACM_VERSION) $(DOCS_REPO_DIR)

fetch-ocp: check-deps
	@mkdir -p tmp
	./scripts/fetch_ocp_docs.sh $(OCP_VERSION) $(OCP_DOCS_REPO_DIR)

process-official: check-deps
	@echo "Processing official docs into flat structure..."
	@mkdir -p $(EXPORT_DIR)
	@find $(DOCS_REPO_DIR) -name "main.adoc" -type f | grep -v "$(DOCS_REPO_DIR)/apis/main.adoc" | while read file; do \
		REL_PATH=$${file#$(DOCS_REPO_DIR)/}; \
		FLAT_NAME=$$(echo $$REL_PATH | sed 's/\//_/g' | sed 's/\.adoc$$/.md/'); \
		TARGET_NAME="acm_$(ACM_VERSION)_$$FLAT_NAME"; \
		echo "Processing ACM $$REL_PATH -> $$TARGET_NAME"; \
		uv run scripts/convert_adoc_to_md.py "$$file" "$(EXPORT_DIR)/$$TARGET_NAME" "scripts/clean_docbook.py"; \
	done

process-ocp: check-deps
	@echo "Processing OpenShift docs into flat structure..."
	@mkdir -p $(EXPORT_DIR)
	@uv run scripts/assemble_ocp_doc.py "$(OCP_DOCS_REPO_DIR)" "$(EXPORT_DIR)/ocp_$(OCP_VERSION)_monitoring.md" "scripts/clean_docbook.py"

fetch-extra: check-deps
	@echo "Fetching extra docs into flat structure..."
	@mkdir -p $(EXPORT_DIR)
	@if [ -f "$(EXTRA_DOCS_CONFIG)" ]; then \
		uv run scripts/fetch_extra_docs.py "$(EXTRA_DOCS_CONFIG)" "$(EXPORT_DIR)" "extra_$(ACM_VERSION)_"; \
	else \
		echo "Info: $(EXTRA_DOCS_CONFIG) not found. Skipping extra docs."; \
	fi

copy-local:
	@echo "Copying local documents into flat structure..."
	@mkdir -p $(EXPORT_DIR)
	@# Copy global static docs
	@if [ -d "static" ]; then \
		for f in static/*; do \
			[ -e "$$f" ] || continue; \
			cp "$$f" "$(EXPORT_DIR)/static_$$(basename $$f)"; \
		done; \
		echo " - Global static docs copied."; \
	fi
	@# Copy version-specific local docs
	@if [ -d "extra_local/$(ACM_VERSION)" ]; then \
		for f in extra_local/$(ACM_VERSION)/*; do \
			[ -e "$$f" ] || continue; \
			cp "$$f" "$(EXPORT_DIR)/local_$(ACM_VERSION)_$$(basename $$f)"; \
		done; \
		echo " - Version-specific local docs ($(ACM_VERSION)) copied."; \
	fi

clean-output:
	@echo "Cleaning export directory..."
	@if [ -d "$(EXPORT_DIR)" ]; then \
		find $(EXPORT_DIR) -mindepth 1 -delete; \
	fi
	@mkdir -p $(EXPORT_DIR)

clean:
	rm -rf tmp/rhacm-docs
	rm -rf tmp/openshift-docs
	rm -rf $(EXPORT_DIR)
	rm -rf .venv
	rm -f uv.lock