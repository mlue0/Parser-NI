# SimpleMeasure

**SimpleMeasure** — desktop-приложение для автоматизации процесса разбраковки кристаллов. Приложение парсит данные из файлов различных форматов и отправляет их на сервер через REST API.

![PyQt6](https://img.shields.io/badge/PyQt6-6.6+-green)
![Python](https://img.shields.io/badge/Python-3.10+-blue)
![License](https://img.shields.io/badge/License-Proprietary-red)

## 🎯 Основные возможности

- 📊 **Парсинг данных** из Excel (XLSX, XLS), CSV и TXT файлов
- ✅ **Валидация данных** через Pydantic с понятными сообщениями об ошибках
- 🔐 **Безопасное хранение** учётных данных в системном keyring
- 🔄 **Автоматические повторы** при сетевых ошибках (exponential backoff)
- 🎨 **Современный UI** с тёмной темой и адаптивным дизайном (16:9)
- 📝 **Подробное логирование** с ротацией файлов
- 🚀 **Готовность к production** с PyInstaller сборкой

## 📋 Требования

- **Python**: 3.10 или выше
- **ОС**: Windows, macOS, Linux
- **Зависимости**: см. `requirements.txt`

## 🚀 Установка

### 1. Клонирование репозитория

```bash
git clone <repository-url>
cd SimpleMeasure
```

### 2. Создание виртуального окружения

```bash
python -m venv .venv
```

### 3. Активация виртуального окружения

**Windows:**
```bash
.venv\Scripts\activate
```

**macOS/Linux:**
```bash
source .venv/bin/activate
```

### 4. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 5. Настройка конфигурации

Скопируйте `.env.example` в `.env` и заполните параметры:

```bash
copy .env.example .env  # Windows
cp .env.example .env    # macOS/Linux
```

Отредактируйте `.env`:

```env
# Базовый URL API
API_URL=https://your-api-server.com/api

# Учётные данные (опционально, приоритет имеет keyring)
API_LOGIN=your_login
API_PASSWORD=your_password

# Статический токен (альтернатива login/password)
API_TOKEN=

# Уровень логирования: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL=INFO
```

### 6. (Опционально) Безопасное хранение credentials

Для максимальной безопасности используйте системный keyring вместо .env:

```python
from config.credentials import save_credentials, save_token

# Сохранить login/password
save_credentials("your_login", "your_password")

# Или сохранить токен
save_token("your_api_token")
```

## 🎮 Использование

### Запуск приложения

```bash
python main.py
```

### Рабочий процесс

1. **Выбор файла**: При запуске автоматически открывается диалог выбора файла
2. **Парсинг**: Приложение распознаёт формат и извлекает данные
3. **Валидация**: Автоматическая проверка обязательных полей
4. **Редактирование**: Форма с тремя вкладками для проверки/корректировки данных
5. **Подтверждение**: Предпросмотр данных перед отправкой
6. **Отправка**: Асинхронная загрузка на сервер с индикатором прогресса

### Поддерживаемые форматы файлов

#### Excel (.xlsx, .xls)
- Формат «ключ-значение» (колонка A — название, B — значение)
- Или заголовки в первой строке

#### CSV (.csv)
- Автоопределение разделителя (`,`, `;`, `\t`)
- Поддержка кодировок: UTF-8, UTF-8-BOM, CP1251

#### Текст (.txt)
```
* Годные кристаллы- 150
* Бракованные кристаллы- 50
* Маркировка пластины- HV101
```

### Ограничения

- Максимальный размер файла: **100 MB**
- Файлы больше **1 MB**: автоматический индикатор загрузки
- Повторные попытки: **3 раза** с exponential backoff

## 🏗️ Архитектура

```
SimpleMeasure/
├── api/                    # REST API клиент
│   ├── client.py          # HTTP клиент с retry механизмом
│   └── exceptions.py      # Кастомные исключения
├── config/                 # Конфигурация
│   ├── settings.py        # Настройки из .env
│   ├── credentials.py     # Keyring интеграция
│   └── app_state.json     # Последний открытый файл
├── logs/                   # Логирование
│   ├── setup.py           # Настройка logging
│   └── app.log            # Лог-файл (ротация 5×5MB)
├── models/                 # Модели данных
│   └── crystal_data.py    # Pydantic модель
├── parsers/                # Парсеры файлов
│   ├── base.py            # Базовый класс с валидацией
│   ├── csv_parser.py      # CSV парсер
│   ├── excel_parser.py    # Excel парсер
│   ├── txt_parser.py      # TXT парсер
│   └── registry.py        # Автовыбор парсера
├── ui/                     # Графический интерфейс
│   ├── main_window.py     # Главное окно
│   ├── edit_form.py       # Форма редактирования
│   ├── confirm_dialog.py  # Диалог подтверждения
│   ├── loading_dialog.py  # Индикатор загрузки
│   └── workers.py         # Async worker (QThread)
├── tests/                  # Тесты
│   ├── test_api.py
│   ├── test_models.py
│   └── test_parsers.py
└── main.py                 # Точка входа
```

## 🧪 Тестирование

### Запуск всех тестов

```bash
pytest
```

### Запуск с покрытием

```bash
pytest --cov=. --cov-report=html
```

### Запуск конкретного теста

```bash
pytest tests/test_parsers.py -v
```

## 📦 Сборка executable

### Windows

```bash
pyinstaller SimpleMeasure.spec
```

Готовый .exe будет в `dist/SimpleMeasure/`

### Настройка spec файла

Отредактируйте `SimpleMeasure.spec` для кастомизации:

```python
# Название приложения
name='SimpleMeasure'

# Иконка (если есть)
icon='icon.ico'

# Включение дополнительных файлов
datas=[('.env.example', '.')]
```

## 🔧 Настройка API интеграции

### Структура запросов

#### 1. Авторизация

```http
POST {API_URL}/auth/login
Content-Type: application/json

{
  "login": "user",
  "password": "pass"
}
```

**Ответ:**
```json
{
  "token": "jwt-token-here",
  "expires_in": 3600
}
```

#### 2. Отправка данных

```http
POST {API_URL}/crystals/sorting
Authorization: Bearer {token}
Content-Type: application/json

{
  "good_crystals": 150,
  "defective_crystals": 50,
  "plate_marking": "HV101",
  ...
}
```

**Ответ:**
```json
{
  "id": 123,
  "status": "saved",
  "message": "Данные успешно сохранены"
}
```

### Адаптация под свой API

Отредактируйте `api/client.py`:

```python
# Изменить URL endpoints
url = f"{self.base_url}/your/custom/endpoint"

# Изменить формат payload
payload = {
    "custom_field_1": data.field1,
    "custom_field_2": data.field2,
}

# Изменить парсинг ответа
token = data.get("your_token_field")
```

## 📊 Модель данных

### Основные поля

| Поле | Тип | Описание | Обязательное |
|------|-----|----------|--------------|
| `good_crystals` | int | Годные кристаллы | ✅ |
| `defective_crystals` | int | Бракованные | ✅ |
| `plate_marking` | str | Маркировка пластины | ✅ |
| `bmk_batch_number` | str | Номер партии БМК | ✅ |
| `plate_number` | str | Номер пластины | ✅ |
| `sorting_type` | str | Тип разбраковки | ✅ |
| `sorting_target` | str | ПР-ОВ или ОКР | ✅ |

### Типы брака

- `defect_contact` — Брак по Contact
- `defect_icc` — Брак по ICC
- `defect_fc` — Брак по FC
- `defect_static` — Брак по Static
- `defect_inl` — Брак по INL
- `defect_dnl` — Брак по DNL
- `defect_burn` — Брак по Burn
- `defect_u0_adc` — Брак по U0 в режиме АЦП

### Нормы

- `norm_inl`, `norm_dnl`, `norm_ufs`, `norm_u0`
- `norm_u_perzhiganiya`, `norm_u0_adc`

## 🔐 Безопасность

### Хранение credentials

1. **Keyring (рекомендуется)**: Системное хранилище
   - Windows: Credential Manager
   - macOS: Keychain
   - Linux: Secret Service API

2. **.env файл**: Для разработки
   - Добавлен в `.gitignore`
   - Не коммитится в репозиторий

### Сетевая безопасность

- **HTTPS только**: HTTP запросы отклоняются
- **Timeout**: 30 секунд по умолчанию
- **Retry policy**: Только для безопасных методов
- **Token refresh**: Автоматическая повторная авторизация

## 📝 Логирование

### Уровни

- **DEBUG**: Детальная информация для отладки
- **INFO**: Основные события (по умолчанию)
- **WARNING**: Предупреждения
- **ERROR**: Ошибки с возможностью продолжения
- **CRITICAL**: Критические ошибки

### Конфигурация

```env
LOG_LEVEL=INFO  # Измените на DEBUG для отладки
```

### Расположение логов

```
logs/
├── app.log       # Текущий лог
├── app.log.1     # Предыдущий
├── app.log.2
├── app.log.3
├── app.log.4
└── app.log.5
```

**Ротация**: 5 файлов × 5 MB = 25 MB total

## 🐛 Troubleshooting

### Ошибка "Файл не найден"

```bash
# Проверьте путь
ls -la c:\Programms\SimpleMeasure\
```

### Ошибка импорта keyring

```bash
pip install --upgrade keyring
```

### Ошибка авторизации API

1. Проверьте `.env` файл
2. Проверьте keyring: `python -c "from config.credentials import get_login; print(get_login())"`
3. Проверьте логи: `tail logs/app.log`

### Ошибка парсинга Excel

```bash
# Переустановите openpyxl
pip uninstall openpyxl
pip install openpyxl>=3.1.0
```

## 🤝 Contributing

1. Fork репозитория
2. Создайте feature branch: `git checkout -b feature/amazing-feature`
3. Commit изменения: `git commit -m 'Add amazing feature'`
4. Push в branch: `git push origin feature/amazing-feature`
5. Откройте Pull Request

### Code Style

- **Python**: PEP 8, type hints обязательны
- **Docstrings**: Google style
- **Imports**: isort
- **Formatting**: black

## 📄 Лицензия

Proprietary. Все права защищены.

## 👥 Авторы

- Development Team — initial work

## 📞 Поддержка

Для вопросов и поддержки:
- 📧 Email: support@example.com
- 📖 Wiki: [Documentation](https://wiki.example.com)
- 🐛 Issues: [GitHub Issues](https://github.com/example/simplemeasure/issues)

---

**SimpleMeasure** — Автоматизация разбраковки кристаллов. Made with ❤️
