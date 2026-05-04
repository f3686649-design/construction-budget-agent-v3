# Внедрение Construction Budget Agent v3

Docker-версия теперь использует вариант C: React frontend + FastAPI backend.
Старая Streamlit-версия в Docker больше не запускается.

## 1. Пользователи и пароли

Перед первым запуском создайте рабочий `users.json` из примера:

```powershell
Copy-Item users.example.json users.json
```

`users.example.json` содержит только демонстрационные учётные записи:

- `admin / admin123`
- `user / user123`

Перед внедрением обязательно смените пароли. Пароли в `users.json` хранятся только в виде PBKDF2-хэша.

Чтобы создать хэш нового пароля:

```powershell
.\.venv\Scripts\python.exe -c "from backend.auth import hash_password; print(hash_password('НОВЫЙ_ПАРОЛЬ'))"
```

Замените значение `password_hash` у нужного пользователя в `users.json`.

`users.json` не коммитится в репозиторий и добавлен в `.gitignore`, потому что это локальный файл с доступами конкретной организации.

## 2. Запуск через Docker

Создайте `.env` из примера:

```powershell
Copy-Item .env.example .env
```

Запустите два контейнера:

```powershell
docker compose up -d --build
```

После запуска откройте:

```text
http://localhost
```

Проверка API:

```text
http://localhost/api/health
```

Backend дополнительно доступен напрямую:

```text
http://localhost:8000/api/health
```

## 3. Если порт 80 занят

Откройте `.env` и замените:

```text
FRONTEND_PORT=80
```

на:

```text
FRONTEND_PORT=8080
```

Перезапустите контейнеры:

```powershell
docker compose up -d --build
```

После этого frontend будет доступен по адресу:

```text
http://localhost:8080
```

API через nginx будет работать так:

```text
http://localhost:8080/api/health
```

## 4. Состав контейнеров

`backend`:

- собирается через `Dockerfile.backend`;
- запускает FastAPI командой `uvicorn backend.main:app --host 0.0.0.0 --port 8000`;
- публикует порт `8000:8000`;
- сохраняет файлы в volume-папки проекта.

`frontend`:

- собирается через `Dockerfile.frontend`;
- выполняет production build React/Vite;
- отдаёт `dist` через nginx;
- публикует порт `80:80`;
- проксирует `/api/*` на `backend:8000`.

## 5. Переменные окружения

Файл `.env.example`:

```text
BACKEND_PORT=8000
FRONTEND_PORT=80
VITE_API_BASE_URL=/api
AUTH_SECRET=change-this-secret-before-deploy
AUTH_TOKEN_TTL_SECONDS=43200
```

Перед внедрением замените `AUTH_SECRET` на длинную случайную строку. Для офисной сети обычно достаточно менять только `FRONTEND_PORT`, если порт `80` занят.

## 6. Где хранятся файлы

История проектов:

```text
backend/storage/projects
```

Excel-файлы:

```text
backend/storage/outputs
```

Загрузки пользователя:

```text
backend/storage/uploads
```

Каждый расчёт API сохраняется в:

```text
backend/storage/projects/{project_id}
```

Внутри папки проекта:

- `input.json`
- `result.json`
- `metadata.json`
- Excel-файл

В `metadata.json` сохраняется пользователь, который выполнил расчёт.

## 7. Резервная копия

Регулярно копируйте:

```text
backend/storage/projects
backend/storage/outputs
backend/storage/uploads
users.json
```

Пример:

```powershell
$Date = Get-Date -Format "yyyyMMdd_HHmm"
New-Item -ItemType Directory -Force -Path ".\backup\$Date"
Copy-Item ".\backend\storage\projects" ".\backup\$Date\projects" -Recurse
Copy-Item ".\backend\storage\outputs" ".\backup\$Date\outputs" -Recurse
Copy-Item ".\backend\storage\uploads" ".\backup\$Date\uploads" -Recurse
Copy-Item ".\users.json" ".\backup\$Date\users.json"
```

## 8. Запуск без Docker для разработки

Backend:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --port 8000
```

Frontend:

```powershell
cd frontend
npm install
npm run dev
```

Frontend будет доступен на:

```text
http://localhost:5173
```

Vite проксирует `/api` на `http://localhost:8000`.

## 9. Проверка перед внедрением

Backend:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Frontend:

```powershell
cd frontend
npm run build
```
