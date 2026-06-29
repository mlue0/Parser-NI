# Contributing to SimpleMeasure

Спасибо за интерес к улучшению SimpleMeasure! Этот документ содержит рекомендации по внесению вклада в проект.

## 📋 Содержание

- [Code of Conduct](#code-of-conduct)
- [Как помочь](#как-помочь)
- [Процесс разработки](#процесс-разработки)
- [Настройка окружения](#настройка-окружения)
- [Coding Guidelines](#coding-guidelines)
- [Тестирование](#тестирование)
- [Commit Guidelines](#commit-guidelines)
- [Pull Request Process](#pull-request-process)

## Code of Conduct

Мы ожидаем, что все участники будут вести себя профессионально и уважительно. Недопустимы:
- Оскорбления и личные нападки
- Харассмент в любой форме
- Публикация личной информации других людей
- Непрофессиональное или неэтичное поведение

## Как помочь

Вы можете помочь проекту следующими способами:

### 🐛 Сообщения об ошибках

Перед созданием issue проверьте, что похожая проблема ещё не была зарегистрирована. Включите в отчёт:

- Версию SimpleMeasure
- Операционную систему
- Версию Python
- Шаги для воспроизведения
- Ожидаемое и фактическое поведение
- Логи из `logs/app.log`
- Скриншоты (если применимо)

### 💡 Предложения функций

Создайте issue с тегом `enhancement` и опишите:

- Проблему, которую решает функция
- Предложенное решение
- Альтернативные варианты
- Как это повлияет на существующий функционал

### 🔧 Исправления кода

1. Найдите issue с тегом `good first issue` или `help wanted`
2. Оставьте комментарий, что берётесь за задачу
3. Следуйте процессу разработки (см. ниже)

## Процесс разработки

### 1. Fork и клонирование

```bash
# Fork репозитория через GitHub UI
# Затем клонируйте ваш fork
git clone https://github.com/YOUR_USERNAME/SimpleMeasure.git
cd SimpleMeasure
```

### 2. Создание ветки

```bash
# Создайте ветку от main
git checkout -b feature/your-feature-name

# Или для bug fix
git checkout -b fix/issue-123
```

Naming convention для веток:
- `feature/` — новая функциональность
- `fix/` — исправление бага
- `refactor/` — рефакторинг без изменения API
- `docs/` — изменения документации
- `test/` — добавление/исправление тестов

### 3. Внесение изменений

Следуйте [Coding Guidelines](#coding-guidelines) и пишите чистый, читаемый код.

### 4. Коммит

Следуйте [Commit Guidelines](#commit-guidelines) для единообразия истории.

### 5. Push и PR

```bash
git push origin feature/your-feature-name
```

Откройте Pull Request через GitHub UI.

## Настройка окружения

### Требования

- Python 3.10+
- pip или poetry

### Установка зависимостей

```bash
# Создание виртуального окружения
python -m venv .venv

# Активация (Windows)
.venv\Scripts\activate

# Активация (macOS/Linux)
source .venv/bin/activate

# Установка зависимостей
pip install -r requirements.txt

# Установка dev зависимостей
pip install pytest pytest-qt pytest-cov black isort mypy ruff
```

### Настройка .env

```bash
copy .env.example .env  # Windows
cp .env.example .env    # macOS/Linux
```

Отредактируйте `.env` с тестовыми credentials.

## Coding Guidelines

### Python Style

Следуем **PEP 8** с некоторыми дополнениями:

- **Line length**: 100 символов (не 79)
- **Quotes**: Двойные кавычки `"` для строк
- **Type hints**: Обязательны для всех функций
- **Docstrings**: Google style для всех public методов

### Форматирование

```bash
# Black для автоформатирования
black .

# isort для сортировки импортов
isort .

# Проверка стиля
ruff check .
```

### Type Checking

```bash
# mypy для проверки типов
mypy main.py api/ models/ parsers/ ui/
```

### Примеры кода

#### Good ✅

```python
from __future__ import annotations

from pathlib import Path
from typing import Any


def parse_file(file_path: str | Path) -> dict[str, Any]:
    """Парсит файл и возвращает словарь с данными.
    
    Args:
        file_path: Путь к файлу для парсинга
        
    Returns:
        Словарь с распарсенными данными
        
    Raises:
        ParserError: Если файл не может быть распарсен
    """
    path = Path(file_path)
    
    if not path.exists():
        raise ParserError(f"Файл не найден: {path}")
    
    # Implementation
    return {}
```

#### Bad ❌

```python
# Нет type hints
def parse_file(file_path):
    # Нет docstring
    path = Path(file_path)
    if not path.exists():
        raise Exception("File not found")  # Неспецифичное исключение
    return {}  # Непонятный return type
```

### Структура модулей

```python
"""Краткое описание модуля."""

from __future__ import annotations  # Всегда первый импорт

# Стандартная библиотека
import os
import sys
from pathlib import Path

# Сторонние библиотеки
import pandas as pd
from PyQt6.QtWidgets import QWidget

# Локальные импорты
from api.client import ApiClient
from models.crystal_data import CrystalData


# Константы в UPPER_CASE
MAX_FILE_SIZE = 100 * 1024 * 1024

# Классы и функции
```

## Тестирование

### Запуск тестов

```bash
# Все тесты
pytest

# С покрытием
pytest --cov=. --cov-report=html

# Только юнит-тесты
pytest -m unit

# Только UI тесты
pytest -m ui

# Verbose режим
pytest -v

# Один конкретный файл
pytest tests/test_api.py -v
```

### Написание тестов

- **Unit tests**: Изолированные, быстрые, без зависимостей
- **Integration tests**: Проверка взаимодействия компонентов
- **UI tests**: С pytest-qt для GUI компонентов

Пример:

```python
import pytest
from models.crystal_data import CrystalData


class TestCrystalData:
    """Тесты модели CrystalData."""
    
    def test_valid_data(self):
        """Тест валидных данных."""
        data = CrystalData(
            good_crystals=100,
            # ... все обязательные поля
        )
        assert data.good_crystals == 100
    
    def test_invalid_data_raises_error(self):
        """Тест что невалидные данные вызывают ошибку."""
        with pytest.raises(ValidationError):
            CrystalData(good_crystals=-10)  # Негативное число
```

### Coverage

Стремитесь к покрытию >80% для нового кода. Проверить:

```bash
pytest --cov=. --cov-report=term-missing
```

## Commit Guidelines

Используем **Conventional Commits**:

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat`: Новая функция
- `fix`: Исправление бага
- `docs`: Изменения документации
- `style`: Форматирование, отступы (без изменения кода)
- `refactor`: Рефакторинг кода
- `test`: Добавление/изменение тестов
- `chore`: Изменения в build, CI/CD

### Примеры

```bash
# Новая функция
git commit -m "feat(api): добавлен retry механизм для API запросов"

# Исправление бага
git commit -m "fix(parser): исправлена обработка пустых файлов"

# Документация
git commit -m "docs(readme): обновлена инструкция по установке"

# Тесты
git commit -m "test(api): добавлены тесты для retry логики"
```

### Правила

- Используйте императивное наклонение ("добавлен", а не "добавил")
- Первая строка не более 72 символов
- Тело коммита объясняет "что" и "почему", а не "как"
- Ссылайтесь на issues: `Closes #123` или `Refs #456`

## Pull Request Process

### Перед созданием PR

1. ✅ Все тесты проходят: `pytest`
2. ✅ Код отформатирован: `black . && isort .`
3. ✅ Нет lint ошибок: `ruff check .`
4. ✅ Type hints корректны: `mypy .`
5. ✅ Добавлены тесты для нового кода
6. ✅ Документация обновлена (если нужно)
7. ✅ CHANGELOG.md обновлён

### Описание PR

Хороший PR включает:

**Заголовок**: Краткое описание (50-72 символа)

**Описание**:
- Что изменено и почему
- Ссылка на related issues
- Скриншоты (для UI изменений)
- Чек-лист выполненных требований

**Пример**:

```markdown
## Описание

Добавлен retry механизм для API запросов с exponential backoff.

Closes #123

## Изменения

- Добавлен `max_retries` параметр в ApiClient
- Реализован exponential backoff (0.5s, 1s, 2s)
- Обновлены тесты API клиента
- Документация в README

## Чек-лист

- [x] Тесты проходят
- [x] Код отформатирован
- [x] Документация обновлена
- [x] CHANGELOG.md обновлён
```

### Review Process

1. Maintainer проверит ваш PR
2. Возможно потребуются изменения
3. После approval — merge в main

### После merge

- Ваша ветка будет удалена
- Вы будете добавлены в contributors! 🎉

## Вопросы?

Не стесняйтесь задавать вопросы:

- 📧 Email: support@example.com
- 💬 Создайте discussion в GitHub
- 🐛 Откройте issue для bugs

---

**Спасибо за ваш вклад в SimpleMeasure!** 💙
