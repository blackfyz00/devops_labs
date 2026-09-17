IMAGE_NAME := quotes-scraper
CONTAINER_NAME := quotes-runner

.PHONY: build run clean ci

build:
	docker build -t $(IMAGE_NAME) .

run: build
	mkdir -p out
	docker run --rm \
		-v $(PWD)/out:/app/out \
		--name $(CONTAINER_NAME) \
		$(IMAGE_NAME)

clean:
	docker rmi $(IMAGE_NAME) || true
	rm -rf out

ci: build
	docker run --rm $(IMAGE_NAME) python -m pytest