# Makefile 
TARGET_HOST := 10.30.39.189
TARGET_USER := admin
SSH_KEY := .lab/id_rsa
ANSIBLE_DIR := infra/ansible
DEPLOY_DIR := deploy

.PHONY: setup provision apply_ansible deploy run verify destroy clean logs help

help:
	@echo "Usage:"
	@echo "  make provision      - Generate inventory and check connectivity"
	@echo "  make apply_ansible  - Install Docker via Ansible"
	@echo "  make deploy         - Build and run containers"
	@echo "  make run URL=...    - Send job to Redis"
	@echo "  make verify         - Check results"

setup:
	@mkdir -p .lab
	@test -f $(SSH_KEY) || ssh-keygen -t ed25519 -f $(SSH_KEY) -N "" -q
	@chmod 600 $(SSH_KEY)
	@echo "==> SSH Key generated."

provision: setup
	@echo "==> Checking SSH connectivity to $(TARGET_HOST)..."; \
	if ! ssh -i $(SSH_KEY) -o StrictHostKeyChecking=no $(TARGET_USER)@$(TARGET_HOST) "echo OK" >/dev/null 2>&1; then \
	  echo "ERROR: Cannot connect to $(TARGET_HOST) as $(TARGET_USER)."; \
	  echo "Ensure SSH server is running in OS and key is authorized."; \
	  exit 1; \
	fi; \
	echo "==> Connectivity OK."; \
	mkdir -p $(ANSIBLE_DIR)/inventories/lab; \
	echo "[lab]" > $(ANSIBLE_DIR)/inventories/lab/hosts.yml; \
	echo "$(TARGET_HOST) ansible_user=$(TARGET_USER) ansible_ssh_private_key_file=$(CURDIR)/$(SSH_KEY) ansible_ssh_common_args='-o StrictHostKeyChecking=no'" >> $(ANSIBLE_DIR)/inventories/lab/hosts.yml; \
	echo "==> Inventory updated."

apply_ansible:
	@echo "==> Running Ansible Playbook..."
	cd $(ANSIBLE_DIR) && ansible-playbook -i inventories/lab/hosts.yml playbooks/site.yml

deploy: 
	@echo "==> Transferring project files to target host..."
	rsync -avz -e "ssh -i $(SSH_KEY) -o StrictHostKeyChecking=no" \
	  --exclude='.git' --exclude='node_modules' --exclude='.lab' \
	  ./Dockerfile ./pyproject.toml ./README.md ./uv.lock ./src ./deploy \
	  $(TARGET_USER)@$(TARGET_HOST):~/app/
	
	@echo "==> Building and Starting Containers on remote host..."
	ssh -i $(SSH_KEY) -o StrictHostKeyChecking=no $(TARGET_USER)@$(TARGET_HOST) \
	  "cd ~/app/deploy && sudo docker compose up -d --build"
	@echo "==> Deployment complete."

run:
	@if [ -z "$(URL)" ]; then echo "Usage: make run URL=https://example.com"; exit 1; fi
	@echo "==> Sending task to Redis on remote host..."
	JOB_ID=$$(openssl rand -hex 8); \
	echo "Job ID: $$JOB_ID"; \
	ssh -i $(SSH_KEY) -o StrictHostKeyChecking=no $(TARGET_USER)@$(TARGET_HOST) \
	  "cd ~/app/deploy && sudo docker compose exec redis redis-cli XADD jobs '*' job_id '$$JOB_ID' url '$(URL)'"
	@echo "Task sent."

verify:
	@echo "==> Verifying results on remote host..."
	@sleep 2
	
	@JOB_ID=$$(ssh -i $(SSH_KEY) -o StrictHostKeyChecking=no $(TARGET_USER)@$(TARGET_HOST) \
	  "cd /home/$(TARGET_USER)/app/deploy && sudo docker compose exec -T scraper find /srv/quotes-scraper/results -maxdepth 1 -name '*.json' -printf '%T@ %f\n' 2>/dev/null | sort -rn | head -n 1 | cut -d' ' -f2 | sed 's/.json$$//'"); \
	if [ -z "$$JOB_ID" ]; then \
	  echo "No JSON files found in results directory."; \
	  exit 1; \
	fi; \
	echo "Found Job ID: $$JOB_ID"; \
	ssh -i $(SSH_KEY) -o StrictHostKeyChecking=no $(TARGET_USER)@$(TARGET_HOST) \
	  "curl -sf http://localhost:8080/results/$$JOB_ID.json > /dev/null && echo 'OK via Nginx' || echo 'FAIL via Nginx'"

logs:
	ssh -i $(SSH_KEY) -o StrictHostKeyChecking=no $(TARGET_USER)@$(TARGET_HOST) \
	  "cd ~/app/deploy && sudo docker compose logs -f"

destroy:
	@echo "==> Cleaning up local artifacts..."
	rm -rf .lab
	rm -rf $(ANSIBLE_DIR)/inventories/lab
	@echo "Note: Remote app data remains. To clean remote: ssh user@host 'rm -rf ~/app'"

clean: destroy
	docker system prune -af 2>/dev/null || true