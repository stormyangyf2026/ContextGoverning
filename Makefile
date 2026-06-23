.PHONY: help up down db-setup backend frontend test clean

help:
	@echo "Context Platform - Development Commands"
	@echo "  make up         Start all services (Docker Compose)"
	@echo "  make down       Stop all services"
	@echo "  make db-setup   Run database migrations"
	@echo "  make backend    Start backend dev server (port 8000)"
	@echo "  make frontend   Start both frontends (admin:3001, user:3002)"
	@echo "  make test       Run all tests"
	@echo "  make clean      Clean build artifacts"

up:
	docker compose up -d db qdrant redis

down:
	docker compose down

db-setup:
	cd backend && alembic upgrade head

backend:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

frontend:
	cd frontend/admin && npm run dev &
	cd frontend/user && npm run dev &
	wait

test:
	cd backend && python -m pytest app/tests/ -v --cov=app --cov-report=term

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf frontend/admin/dist frontend/user/dist 2>/dev/null || true
