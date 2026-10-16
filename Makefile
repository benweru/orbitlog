PYTHON ?= python
VENV ?= .venv
ifeq ($(OS),Windows_NT)
  VPY := $(VENV)/Scripts/python
else
  VPY := $(VENV)/bin/python
endif
# Pure make (no shell syntax) so recipes also work with make on Windows/PowerShell:
# the venv python if it exists, otherwise $(PYTHON).
RUN_PY := $(if $(wildcard $(VPY) $(VPY).exe),$(VPY),$(PYTHON))

.PHONY: setup test test-cfs quick reproduce clean cfs-build cfs-up cfs-logs cfs-down

setup:
	$(PYTHON) -m venv $(VENV)
	$(VPY) -m pip install --upgrade pip
	$(VPY) -m pip install -r requirements-dev.txt
	$(VPY) -m pip install -e .

test:
	$(RUN_PY) -m pytest -q -m "not cfs and not docker and not linux_i2c"

test-cfs:
	$(RUN_PY) -m pytest -q -m cfs

quick:
	@echo "make quick: not yet implemented (target: 3 configs x 10 cases, <30 min on a laptop)."

reproduce:
	@echo "make reproduce: not yet implemented (see docs/plan.md section 6)."

clean:
	rm -rf $(VENV) .pytest_cache build dist src/*.egg-info

# cFS image is pinned to nasa/cFS tag v7.0.1. See docker/README.md.
cfs-build:
	docker build -t orbitlog-cfs docker/cfs

# Foreground run so event messages stay on stdout. --rm drops the container on exit.
# Docker's default fs.mqueue.msg_max is 10, which is below the cFS pipe depth
# (OS_QueueCreate fails with EINVAL). msgqueue ulimit covers the byte budget.
cfs-up:
	docker run --name orbitlog-cfs --rm --ulimit msgqueue=819200 --sysctl fs.mqueue.msg_max=256 --sysctl fs.mqueue.msgsize_max=16384 orbitlog-cfs

cfs-logs:
	docker logs -f orbitlog-cfs

cfs-down:
	docker rm -f orbitlog-cfs

N ?= 30
SEED ?= 0
# Windows equivalent without make:  .venv\Scripts\python -m orbitlog.build_dataset --n 6 --seed 0
.PHONY: dataset
dataset:
	$(RUN_PY) -m orbitlog.build_dataset --n $(N) --seed $(SEED)
