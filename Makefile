IMAGE_NAME := quotes-scraper
CONTAINER_NAME := quotes-worker
FLOCI_PORT := 4566

.PHONY: build provision deploy run destroy clean ci

# Сборка Docker-образа
build:
	docker build -t $(IMAGE_NAME) .

# Развертывание инфраструктуры (Floci + Terraform)
provision:
	docker compose up -d --wait
	@echo "Waiting for Floci to be ready..."
	@sleep 5
	terraform -chdir=infra init
	terraform -chdir=infra apply -auto-approve

# Деплой приложения (сборка + запуск контейнера с конфигами из Terraform)
deploy: build
	$(eval BUCKET_NAME := $(shell terraform -chdir=infra output -raw bucket_name))
	$(eval QUEUE_URL := $(shell terraform -chdir=infra output -raw queue_url))
	@echo "Deploying with BUCKET=$(BUCKET_NAME) and QUEUE=$(QUEUE_URL)"
	docker stop $(CONTAINER_NAME) || true
	docker rm $(CONTAINER_NAME) || true
	docker run -d \
		--name $(CONTAINER_NAME) \
		-e SQS_QUEUE_URL=$(QUEUE_URL) \
		-e S3_BUCKET_NAME=$(BUCKET_NAME) \
		-e AWS_ENDPOINT_URL=http://host.docker.internal:$(FLOCI_PORT) \
		--add-host=host.docker.internal:host-gateway \
		$(IMAGE_NAME)

# Отправка тестового задания в очередь
run:
	$(eval QUEUE_URL := $(shell terraform -chdir=infra output -raw queue_url))
	$(eval ENDPOINT := http://localhost:$(FLOCI_PORT))
	docker run --rm \
		-e SQS_QUEUE_URL=$(QUEUE_URL) \
		-e AWS_ENDPOINT_URL=$(ENDPOINT) \
		-v $(PWD)/scripts:/app/scripts \
		-w /app \
		python:3.12-slim \
		bash -c "pip install boto3 -q && python scripts/send_task.py"

# Уничтожение инфраструктуры
destroy:
	terraform -chdir=infra destroy -auto-approve || true
	docker compose down -v || true
	docker stop $(CONTAINER_NAME) || true
	docker rm $(CONTAINER_NAME) || true

# Очистка артефактов
clean:
	rm -rf out/
	docker rmi $(IMAGE_NAME) || true
	docker system prune -f

# CI проверка
ci:
	terraform fmt -check -recursive infra
	terraform validate -chdir=infra
	pytest