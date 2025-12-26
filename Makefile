IMAGE_NAME = bns-dev:fedora
CONTAINER_NAME = bns-dev
NODE_VERSION ?= 20

.PHONY: build run shell clean

build:
	podman build --tag $(IMAGE_NAME) --build-arg NODE_MAJOR=$(NODE_VERSION) -f Containerfile .

run:
	podman run --rm -it \
		-v $(PWD):/workspace:Z \
		-w /workspace \
		-p 3000:3000 \
		-e LOCAL_UID=$(shell id -u) \
		-e LOCAL_GID=$(shell id -g) \
		--name $(CONTAINER_NAME) \
		$(IMAGE_NAME)

shell: run

clean:
	podman rmi $(IMAGE_NAME) || true
