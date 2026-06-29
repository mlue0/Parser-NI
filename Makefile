# Makefile for SimpleMeasure
# Для Windows используйте: make или mingw32-make

.PHONY: help install test lint format clean run build docs

# Цвета для вывода (работает в Unix shells)
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
NC := \033[0m # No Color

help: ## Показать это сообщение помощи
	@echo "$(BLUE)SimpleMeasure - Makefile команды:$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-15s$(NC) %s\n", $$1, $$2}'
	@echo ""

install: ## Установить зависимости
	@echo "$(BLUE)Установка зависимостей...$(NC)"
	pip install -r requirements.txt
	@echo "$(GREEN)✓ Зависимости установлены$(NC)"

install-dev: install ## Установить dev зависимости
	@echo "$(BLUE)Установка dev зависимостей...$(NC)"
	pip install pytest pytest-qt pytest-cov black isort mypy ruff
	@echo "$(GREEN)✓ Dev зависимости установлены$(NC)"

test: ## Запустить тесты
	@echo "$(BLUE)Запуск тестов...$(NC)"
	pytest
	@echo "$(GREEN)✓ Тесты завершены$(NC)"

test-cov: ## Запустить тесты с покрытием
	@echo "$(BLUE)Запуск тестов с coverage...$(NC)"
	pytest --cov=. --cov-report=html --cov-report=term
	@echo "$(GREEN)✓ Coverage report: htmlcov/index.html$(NC)"

test-ui: ## Запустить только UI тесты
	@echo "$(BLUE)Запуск UI тестов...$(NC)"
	pytest -m ui -v
	@echo "$(GREEN)✓ UI тесты завершены$(NC)"

test-unit: ## Запустить только unit тесты
	@echo "$(BLUE)Запуск unit тестов...$(NC)"
	pytest -m unit -v
	@echo "$(GREEN)✓ Unit тесты завершены$(NC)"

lint: ## Проверить код на ошибки стиля
	@echo "$(BLUE)Проверка стиля кода...$(NC)"
	@echo "$(YELLOW)Running ruff...$(NC)"
	ruff check .
	@echo "$(YELLOW)Running mypy...$(NC)"
	mypy main.py api/ models/ parsers/ config/ || true
	@echo "$(GREEN)✓ Lint проверка завершена$(NC)"

format: ## Форматировать код
	@echo "$(BLUE)Форматирование кода...$(NC)"
	@echo "$(YELLOW)Running black...$(NC)"
	black .
	@echo "$(YELLOW)Running isort...$(NC)"
	isort .
	@echo "$(GREEN)✓ Код отформатирован$(NC)"

format-check: ## Проверить форматирование без изменений
	@echo "$(BLUE)Проверка форматирования...$(NC)"
	black --check .
	isort --check-only .
	@echo "$(GREEN)✓ Форматирование корректно$(NC)"

clean: ## Очистить временные файлы
	@echo "$(BLUE)Очистка временных файлов...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/ 2>/dev/null || true
	rm -rf dist/ build/ 2>/dev/null || true
	rm -f .coverage 2>/dev/null || true
	@echo "$(GREEN)✓ Очистка завершена$(NC)"

clean-logs: ## Очистить логи
	@echo "$(BLUE)Очистка логов...$(NC)"
	rm -f logs/app.log* 2>/dev/null || true
	@echo "$(GREEN)✓ Логи очищены$(NC)"

run: ## Запустить приложение
	@echo "$(BLUE)Запуск SimpleMeasure...$(NC)"
	python main.py

build: ## Собрать executable с PyInstaller
	@echo "$(BLUE)Сборка executable...$(NC)"
	pyinstaller SimpleMeasure.spec
	@echo "$(GREEN)✓ Сборка завершена: dist/SimpleMeasure/$(NC)"

build-clean: clean ## Очистить и собрать заново
	@echo "$(BLUE)Чистая сборка...$(NC)"
	rm -rf dist/ build/ 2>/dev/null || true
	pyinstaller SimpleMeasure.spec
	@echo "$(GREEN)✓ Чистая сборка завершена$(NC)"

setup: ## Первоначальная настройка проекта
	@echo "$(BLUE)Настройка проекта SimpleMeasure...$(NC)"
	@if [ ! -f .env ]; then \
		echo "$(YELLOW)Создание .env из .env.example...$(NC)"; \
		cp .env.example .env; \
		echo "$(GREEN)✓ .env создан (отредактируйте его!)$(NC)"; \
	else \
		echo "$(YELLOW).env уже существует$(NC)"; \
	fi
	@echo "$(BLUE)Установка зависимостей...$(NC)"
	$(MAKE) install
	@echo ""
	@echo "$(GREEN)✓ Проект настроен!$(NC)"
	@echo "$(YELLOW)Следующие шаги:$(NC)"
	@echo "  1. Отредактируйте .env с вашими API credentials"
	@echo "  2. Запустите: make run"

check: format-check lint test ## Полная проверка (format + lint + test)
	@echo "$(GREEN)✓ Все проверки пройдены!$(NC)"

ci: ## CI проверки (для автоматизации)
	@echo "$(BLUE)CI проверки...$(NC)"
	$(MAKE) format-check
	$(MAKE) lint
	$(MAKE) test-cov
	@echo "$(GREEN)✓ CI проверки пройдены$(NC)"

docs-view: ## Открыть coverage отчёт
	@echo "$(BLUE)Открытие coverage отчёта...$(NC)"
	@if [ -f htmlcov/index.html ]; then \
		python -m webbrowser htmlcov/index.html; \
	else \
		echo "$(YELLOW)Coverage отчёт не найден. Запустите: make test-cov$(NC)"; \
	fi

watch: ## Watch mode для тестов
	@echo "$(BLUE)Watch mode (требует pytest-watch)...$(NC)"
	@command -v ptw >/dev/null 2>&1 || { echo "$(YELLOW)Установите pytest-watch: pip install pytest-watch$(NC)"; exit 1; }
	ptw

.DEFAULT_GOAL := help
