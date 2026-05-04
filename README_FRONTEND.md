# React frontend для Construction Budget Agent v3

React-кабинет находится в папке:

```text
frontend
```

## Запуск backend

Из корня проекта запустите FastAPI:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --port 8000
```

Backend должен быть доступен по адресу:

```text
http://localhost:8000
```

## Запуск frontend

Перейдите в папку frontend:

```powershell
cd frontend
npm install
npm run dev
```

Frontend откроется по адресу:

```text
http://localhost:5173
```

## API

По умолчанию frontend обращается к относительному пути:

```text
/api
```

Если нужен другой адрес backend, создайте в папке `frontend` файл `.env`:

```text
VITE_API_BASE_URL=http://localhost:8000/api
```

Используемые endpoints:

- `GET /api/health`
- `POST /api/auth/login`
- `GET /api/auth/me`
- `POST /api/generate-model`
- `GET /api/projects`
- `GET /api/projects/{project_id}`
- `GET /api/download/{filename}`

Все endpoints, кроме `/api/health` и `/api/auth/login`, требуют авторизацию. Frontend сохраняет токен в `localStorage` и передаёт его в `Authorization` header.

## Разделы кабинета

- Главная
- Новый расчёт
- Бюджет
- ГПР
- Продажи
- Кредит и ДДС
- DSCR
- Сценарии
- Оптимизация
- План улучшений
- История проектов

## Как пользоваться

1. Запустите backend на порту `8000`.
2. Запустите frontend на порту `5173`.
3. Войдите по логину и паролю из `users.json`.
4. Откройте раздел `Новый расчёт`.
5. Заполните основные параметры проекта.
6. Нажмите `Сформировать финансовую модель`.
7. После расчёта откроется dashboard, а Excel можно скачать кнопкой `Скачать Excel`.

Все расчёты сохраняются backend API в:

```text
backend/storage/projects/{project_id}
```

Внутри проекта сохраняются `input.json`, `result.json`, `metadata.json` и Excel-файл.
