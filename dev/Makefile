.PHONY: build start stop clean

# Configuration
IMAGE_NAME ?= bns-dev:fedora
CONTAINER_NAME ?= bns-dev
COMPOSE_FILE ?= ./dev/compose.yml
#NODE_VERSION ?= 24

# Targets
build:
	@echo "Building development container image..."
	podman build \
		--tag bns-dev:fedora \
		--build-arg NODE_MAJOR=24 \
		-f ./dev/Containerfile \
		.

start:
	@echo "Starting development container with podman-compose..."
	podman-compose -f $(COMPOSE_FILE) up -d
	@echo "Container started. Use 'podman attach $(CONTAINER_NAME)' or VSCode Dev Containers to connect."

stop:
	@echo "Stopping development container..."
	podman-compose -f $(COMPOSE_FILE) down

clean: stop
	@echo "Removing development container image..."
	podman rmi -f $(IMAGE_NAME) || true
	@echo "Cleanup complete."

# Utility targets
logs:
	@podman-compose -f $(COMPOSE_FILE) logs -f $(CONTAINER_NAME)

shell:
	@podman attach $(CONTAINER_NAME)

rebuild: clean build start
	@echo "Full rebuild and restart complete."

.PHONY: logs shell rebuild
