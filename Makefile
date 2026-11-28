.PHONY: install dev lint test deploy smoke logs clean

install:
	cd backend && pip install -e ".[dev]"
	cd frontend && npm install

dev:
	cd backend && uvicorn src.api:app --reload --port 8000

lint:
	cd backend && ruff check src/ && mypy src/
	cd frontend && npx vue-tsc --noEmit

test:
	cd backend && pytest tests/ -v

deploy:
	@echo "Frontend: push to gh-pages branch"
	cd frontend && npm run build
	@echo "Backend: git push triggers Render auto-deploy"
	@echo "Set env vars in Render dashboard: SUPABASE_URL, SUPABASE_ANON_KEY, CF_ACCOUNT_ID, CF_BROWSER_API_TOKEN, INTERNAL_SECRET, CORS_ORIGINS"

smoke:
	python scripts/smoke_test.py

logs:
	@echo "Check Render dashboard → Logs tab"
	@echo "Or: render logs --service <service-name>"

clean:
	rm -rf backend/__pycache__ backend/.pytest_cache backend/.mypy_cache
	rm -rf frontend/node_modules frontend/dist
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
