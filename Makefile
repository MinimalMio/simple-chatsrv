PYTHON = python3
VENV_DIR = venv
ACTIVATE = $(VENV_DIR)/bin/activate
ENTRY_POINT = server.py
OUTPUT_BIN = chat_server
SHELL := /bin/bash

.PHONY: run
run: venv
	@echo "Running chat server..."
	source $(ACTIVATE) && $(PYTHON) $(ENTRY_POINT)

.PHONY: venv
venv:
	@if [ ! -d $(VENV_DIR) ]; then \
		echo "Creating virtual environment..."; \
		$(PYTHON) -m venv $(VENV_DIR); \
	fi
	source $(ACTIVATE) && pip install -r requirements.txt

.PHONY: clean
clean:
	@echo "Cleaning up..."
	rm -rf $(VENV_DIR)

.PHONY: package
package: venv
	@echo "Packaging chat server..."
	source $(ACTIVATE) && pip install pyinstaller
	source $(ACTIVATE) && pyinstaller --onefile $(ENTRY_POINT) --name $(OUTPUT_BIN)

.PHONY: clean-package
clean-package:
	@echo "Cleaning up build files..."
	rm -rf dist build __pycache__ *.spec
