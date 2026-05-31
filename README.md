# Learning Analytics Platform

## Актуальная версия

- Backend: `1.2.0`
- Frontend: `1.2.0`

## Особенности

- FastAPI backend с JWT-аутентификацией и ролями `student`, `teacher`, `admin`
- Angular frontend с личным кабинетом, курсами, аналитикой, рекомендациями и тестами
- Уроки в блоковом формате: текстовые секции, callout-блоки, таблицы, графики, карточки-метрики и изображения
- Автоматическая инициализация SQLite-схемы при старте backend
- Вводный курс и вводный опрос уже приведены к актуальному формату контента
- Поле сложности курса хранится как число от `1` до `10`

## Зависимости

### Backend

- `fastapi>=0.115,<1.0`
- `uvicorn>=0.30,<1.0`
- `sqlalchemy>=2.0,<3.0`
- `PyJWT>=2.8,<3.0`

### Frontend

- `@angular/common ^21.2.0`
- `@angular/compiler ^21.2.0`
- `@angular/core ^21.2.0`
- `@angular/forms ^21.2.0`
- `@angular/platform-browser ^21.2.0`
- `@angular/router ^21.2.0`
- `rxjs ~7.8.0`
- `tslib ^2.3.0`

Dev dependencies frontend:

- `@angular/build ^21.2.6`
- `@angular/cli ^21.2.6`
- `@angular/compiler-cli ^21.2.0`
- `jsdom ^28.0.0`
- `prettier ^3.8.1`
- `typescript ~5.9.2`
- `vitest ^4.0.8`

## Структура проекта

- `backend/` — FastAPI-приложение, API, модели, схемы, аналитика и bootstrap БД
- `frontend/` — Angular-приложение с пользовательским интерфейсом
- `app.db` — основная SQLite-база проекта
- `requirements.txt` — Python-зависимости backend
- `BackendUpdates.md` — актуальные backend-изменения и контракт версии

## Как запускать модули

### Запуск backend

1. Активировать виртуальное окружение:

```powershell
.\venv\Scripts\Activate.ps1
```

2. Установить зависимости:

```powershell
pip install -r requirements.txt
```

3. Запустить backend:

```powershell
uvicorn backend.main:app --reload
```

4. Открыть документацию API:

- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/redoc`

### Запуск frontend

1. Перейти в каталог frontend:

```powershell
cd frontend
```

2. Установить зависимости:

```powershell
npm install
```

3. Запустить frontend:

```powershell
npm start
```

4. Открыть приложение:

- `http://localhost:4200`

## База данных

- По умолчанию backend использует корневой файл `app.db`
- При старте backend автоматически:
  - создаёт отсутствующие таблицы
  - добавляет новые колонки для актуальной версии схемы
  - синхронизирует вводный курс и блоковый формат уроков
- Если backend уже был запущен до обновления, его нужно перезапустить
