PYTHON ?= python
VENV ?= .venv
ifeq ($(OS),Windows_NT)
  VPY := $(VENV)/Scripts/python
else
  VPY := $(VENV)/bin/python
endif

.PHONY: setup test quick reproduce clean

setup:
	$(PYTHON) -m venv $(VENV)
	$(VPY) -m pip install --upgrade pip
	$(VPY) -m pip install -r requirements-dev.txt
	$(VPY) -m pip install -e .

test:
	@if [ -x "$(VPY)" ]; then $(VPY) -m pytest -q; else $(PYTHON) -m pytest -q; fi

quick:
	@echo "make quick: not yet implemented (target: 3 configs x 10 cases, <30 min on a laptop)."

reproduce:
	@echo "make reproduce: not yet implemented (see docs/plan.md section 6)."

clean:
	rm -rf $(VENV) .pytest_cache build dist src/*.egg-info
