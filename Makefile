IMAGE_NAME = bns-dev:fedora
CONTAINER_NAME = bns-dev
NODE_VERSION ?= 20

.PHONY: build run shell clean clean-all remove-container

build-container:
	podman build --tag $(IMAGE_NAME) --build-arg NODE_MAJOR=$(NODE_VERSION) -f Containerfile .

run-container:
	podman run \
		--rm -it -d \
		-v $(PWD):/workspace:Z \
		-w /workspace \
		--userns=keep-id \
		--cap-add=NET_RAW \
		-p 3000:3000 \
		-e LOCAL_GID=$(shell id -g) \
		--user $(shell id -u):$(shell id -g) \
		--hostname 'host_'$(CONTAINER_NAME) \
		--name $(CONTAINER_NAME) \
		$(IMAGE_NAME)



remove-container:
	podman rm -f $(CONTAINER_NAME) || true

clean-all:
	# Force stop and remove container if exists, then remove image
	podman rm -f $(CONTAINER_NAME) || true
	podman rmi -f $(IMAGE_NAME) || true

clean-image:
	podman rmi $(IMAGE_NAME) || true

ds-up:
	podman-compose -f devops/docker-compose.yml up -d

ds-down:
	podman-compose -f devops/docker-compose.yml down

ds-logs:
	podman-compose -f devops/docker-compose.yml logs -f