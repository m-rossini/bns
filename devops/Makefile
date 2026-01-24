IMAGE_NAME = bns-dev:fedora
CONTAINER_NAME = bns-dev
NODE_VERSION ?= 20

.PHONY: shell
oo-up:
	podman-compose -f devops/app-compose.yml up -d

oo-down:
	podman-compose -f devops/app-compose.yml down

oo-logs:
	podman-compose -f devops/app-compose.yml logs -f