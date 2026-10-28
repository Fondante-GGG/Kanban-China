.PHONY: help install build up down restart logs test test-backend test-frontend build-frontend migrate seed lint clean

PYTHON ?= python3
VENV_PYTHON ?= backend/venv/bin/python

help: ## Показать справку по доступным командам
	@echo "======================================================================"
	@echo "  Команды управления проектом Yrys Micro-services (Kanban)"
	@echo "======================================================================"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Установить зависимости бэкенда и фронтенда
	@echo "==> Установка зависимостей бэкенда..."
	$(VENV_PYTHON) -m pip install -r backend/requirements.txt
	@echo "==> Установка зависимостей фронтенда..."
	cd frontend && npm ci

build: ## Собрать Docker-образы проекта
	docker compose build

up: ## Запустить все сервисы в Docker (демон)
	docker compose up -d

down: ## Остановить и удалить Docker-контейнеры
	docker compose down

restart: ## Перезапустить контейнеры Docker
	docker compose down && docker compose up -d

logs: ## Просмотр логов Docker-контейнеров
	docker compose logs -f

test: test-backend test-frontend ## Запустить все тесты (бэкенд и фронтенд)

test-backend: ## Запустить unit-тесты бэкенда (Django)
	@echo "==> Запуск тестов Django бэкенда..."
	$(VENV_PYTHON) backend/manage.py test backend.tests

test-frontend: ## Запустить линтинг и проверку типов фронтенда
	@echo "==> Запуск проверки кода фронтенда..."
	cd frontend && npm run lint

build-frontend: ## Собрать фронтенд для продакшена (Next.js)
	@echo "==> Сборка Next.js фронтенда..."
	cd frontend && npm run build

migrate: ## Применить миграции базы данных Django
	$(VENV_PYTHON) backend/manage.py migrate

seed: ## Заполнить базу данных начальными демо-данными
	$(VENV_PYTHON) backend/seed_data.py

lint: test-frontend ## Проверить стиль и качество кода

clean: ## Очистить временные файлы и артефакты сборки
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	rm -rf frontend/.next
	rm -rf frontend/out
