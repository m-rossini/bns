# Makefile for Bean World simulation
#
# Local development uses a Python venv.
# Container builds use Podman (preferred) or Docker.

SHELL := /bin/bash
PYTHON ?= python3
VENV := .venv
PIP := $(VENV)/bin/pip
PYTHON_BIN := $(VENV)/bin/python
ARCADE_STAMP := $(VENV)/.arcade-installed
MAIN_MODULE := sim.main

# Detect container runtime: podman has priority, fall back to docker
CONTAINER_RUNTIME := $(shell command -v podman 2>/dev/null || command -v docker 2>/dev/null || echo "")
CONTAINER_IMAGE := bean-world:latest
CONTAINER_NAME := bean-world

.PHONY: all venv install run run-local run-headless build run-container run-container-ui logs status stop clean help check-env

all: install

check-env:
	@echo "--- Environment ---"
	@echo "Python:   $$($(PYTHON) --version 2>&1)"
	@echo "Venv:     $$([ -d $(VENV) ] && echo "exists at $(VENV)" || echo "not created")"
	@if [ -n "$(CONTAINER_RUNTIME)" ]; then \
		echo "Container runtime: $(CONTAINER_RUNTIME) ($$($(CONTAINER_RUNTIME) --version 2>/dev/null | head -1))"; \
	else \
		echo "Container runtime: none found (podman/docker)"; \
	fi

# --- Local venv targets ---

# Prefer the stdlib venv module. Some minimal Ubuntu images ship python3
# without ensurepip; fall back to `virtualenv`, which bundles its own pip.
$(VENV)/bin/activate:
	@if $(PYTHON) -c "import ensurepip" >/dev/null 2>&1; then \
		echo "$(PYTHON) -m venv $(VENV)"; \
		$(PYTHON) -m venv $(VENV) || { rm -rf $(VENV); \
			echo ""; \
			echo "Error: could not create $(VENV)."; \
			echo "On Debian/Ubuntu install the venv module:"; \
			echo "  sudo apt install python3.10-venv"; \
			exit 1; }; \
	elif $(PYTHON) -m virtualenv --version >/dev/null 2>&1; then \
		echo "ensurepip unavailable; using virtualenv instead"; \
		rm -rf $(VENV); \
		$(PYTHON) -m virtualenv -q $(VENV) || { rm -rf $(VENV); \
			echo "Error: virtualenv failed to create $(VENV)."; \
			exit 1; }; \
	else \
		echo ""; \
		echo "Error: cannot create $(VENV): this Python has no ensurepip."; \
		echo "Install one of these, then run make venv again:"; \
		echo "  sudo apt install python3.10-venv"; \
		echo "  sudo apt install python3-virtualenv"; \
		exit 1; \
	fi

venv: $(VENV)/bin/activate

# Installed lazily; delete the stamp to force a reinstall.
$(ARCADE_STAMP): | venv
	$(PIP) install --upgrade pip
	$(PIP) install arcade
	@touch $(ARCADE_STAMP)

install: $(ARCADE_STAMP)

run-local: $(ARCADE_STAMP)
	$(PYTHON_BIN) -m $(MAIN_MODULE)

# Bounded headless run (no window, no display server needed)
run-headless: $(ARCADE_STAMP)
	BEAN_HEADLESS=1 BEAN_HEADLESS_FRAMES=$${BEAN_HEADLESS_FRAMES:-600} \
		$(PYTHON_BIN) -m $(MAIN_MODULE)

# --- Container targets ---

build:
	@if [ -z "$(CONTAINER_RUNTIME)" ]; then \
		echo "Error: no container runtime (podman/docker) found."; \
		exit 1; \
	fi
	$(CONTAINER_RUNTIME) build -t $(CONTAINER_IMAGE) -f Containerfile .

# `make run` is the safe default: headless in a container, exits on its own.
run: run-container

# Containers run detached (`-d`). Follow output with `make logs`,
# shut down with `make stop`, inspect with `make status`.
run-container: build
	@if [ -z "$(CONTAINER_RUNTIME)" ]; then \
		echo "Error: no container runtime (podman/docker) found."; \
		exit 1; \
	fi
	-$(CONTAINER_RUNTIME) rm -f $(CONTAINER_NAME) >/dev/null 2>&1 || true
	$(CONTAINER_RUNTIME) run -d --init \
		--env BEAN_HEADLESS=1 \
		--env BEAN_HEADLESS_FRAMES=$${BEAN_HEADLESS_FRAMES:-600} \
		--name $(CONTAINER_NAME) \
		$(CONTAINER_IMAGE)
	@echo "Started $(CONTAINER_NAME) detached. Follow it with: make logs"

# Windowed run inside the container using the host X11 server.
# Requires an X session and access to /tmp/.X11-unix (see `xhost`).
run-container-ui: build
	@if [ -z "$(CONTAINER_RUNTIME)" ]; then \
		echo "Error: no container runtime (podman/docker) found."; \
		exit 1; \
	fi
	@if [ -z "$$DISPLAY" ]; then \
		echo "Error: DISPLAY is not set; an X11 session is required for the UI."; \
		exit 1; \
	fi
	@socket=/tmp/.X11-unix/X$$(d=$${DISPLAY#*:}; echo $${d%%.*}); \
	if [ ! -S "$$socket" ]; then \
		echo "Warning: $$socket not found; X forwarding may fail."; \
	fi; \
	auth=$${XAUTHORITY:-$$HOME/.Xauthority}; \
	auth_args=""; \
	if [ -f "$$auth" ]; then \
		auth_args="--volume $$auth:/root/.Xauthority:ro --env XAUTHORITY=/root/.Xauthority"; \
	fi; \
	$(CONTAINER_RUNTIME) rm -f $(CONTAINER_NAME) >/dev/null 2>&1 || true; \
	$(CONTAINER_RUNTIME) run -d --init \
		--security-opt label=disable \
		--env DISPLAY=$$DISPLAY \
		--env BEAN_HEADLESS=0 \
		--volume /tmp/.X11-unix:/tmp/.X11-unix:ro \
		$$auth_args \
		--name $(CONTAINER_NAME) \
		$(CONTAINER_IMAGE)
	@echo "Started $(CONTAINER_NAME) detached. Follow it with: make logs"

# Follow the detached container's output (Ctrl-C stops following only).
logs:
	@$(CONTAINER_RUNTIME) logs -f $(CONTAINER_NAME)

# Show the detached container's status.
status:
	@$(CONTAINER_RUNTIME) ps -a --filter name=$(CONTAINER_NAME) \
		--format 'table {{.Names}}\t{{.Status}}\t{{.Image}}'

# Stop and remove the detached container.
stop:
	@$(CONTAINER_RUNTIME) stop $(CONTAINER_NAME) >/dev/null 2>&1 || true
	@$(CONTAINER_RUNTIME) rm -f $(CONTAINER_NAME) >/dev/null 2>&1 || true
	@echo "Stopped and removed $(CONTAINER_NAME)"

# --- Cleanup ---

clean:
	rm -rf $(VENV)
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@if [ -n "$(CONTAINER_RUNTIME)" ]; then \
		$(CONTAINER_RUNTIME) rm -f $(CONTAINER_NAME) 2>/dev/null || true; \
		$(CONTAINER_RUNTIME) rmi $(CONTAINER_IMAGE) 2>/dev/null || true; \
	fi

# --- Help ---

help:
	@echo "Bean World - Make targets"
	@echo ""
	@echo "Quick start:"
	@echo "  make run         Headless run in a container, detached (600 frames)"
	@echo ""
	@echo "Local development (run these in this order):"
	@echo "  1. make venv         Create the Python virtual environment (.venv)"
	@echo "  2. make install      Install dependencies (arcade) into .venv"
	@echo "  3. make run-local    Run the simulation locally (opens the window)"
	@echo "     make run-headless Run bounded headless locally (no window)"
	@echo "  If 'make venv' fails, install the venv module:"
	@echo "       sudo apt install python3.10-venv"
	@echo ""
	@echo "Containers (podman preferred, falls back to docker), detached:"
	@echo "  make check-env         Show Python/venv/container runtime status"
	@echo "  make build             Build container image (Containerfile)"
	@echo "  make run-container     Start headless container detached (no UI)"
	@echo "  make run-container-ui  Start UI container detached (needs X11)"
	@echo "  make logs              Follow the running container's output"
	@echo "  make status            Show the container's status"
	@echo "  make stop              Stop and remove the container"
	@echo ""
	@echo "  BEAN_HEADLESS_FRAMES=200 make run-container   Override frame count"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean   Remove venv, caches, container, image"
	@echo "  make help    Show this help"
