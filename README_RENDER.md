# Деплой Construction Budget Agent v3 на Render Free

Этот вариант нужен для бесплатного запуска как один Docker Web Service. В одном контейнере собирается React frontend, запускается FastAPI backend, запускается nginx, а nginx отдаёт интерфейс и проксирует `/api` на backend.

Render сам задаёт переменную окружения `PORT`. Контейнер использует её в nginx-конфиге.

## 1. Как создать Render аккаунт

1. Откройте [render.com](https://render.com).
2. Создайте аккаунт или войдите через GitHub.
3. Подключите GitHub-репозиторий с проектом.

## 2. Как создать Web Service

1. В Render нажмите `New +`.
2. Выберите `Web Service`.
3. Выберите GitHub-репозиторий `construction-budget-agent-v3`.
4. В настройках сервиса укажите:

```text
Runtime: Docker
Dockerfile Path: Dockerfile.render
Plan: Free
```

5. Нажмите `Create Web Service`.

Если используете Blueprint, можно загрузить `render.yaml`: он уже указывает `Dockerfile.render` и бесплатный план.

## 3. Переменные окружения

Для первого администратора задайте:

```text
APP_ADMIN_USERNAME=admin
APP_ADMIN_PASSWORD=свой_надёжный_пароль
APP_ADMIN_ROLE=admin
```

Рекомендуется также задать:

```text
AUTH_SECRET=случайная_длинная_строка
```

Если `APP_ADMIN_USERNAME` и `APP_ADMIN_PASSWORD` не заданы, контейнер создаст демо `users.json` из `users.example.json`. Для публичного доступа лучше не оставлять демо-пароли.

## 4. Как запускается контейнер

`Dockerfile.render`:

- собирает React frontend через Node;
- устанавливает Python-зависимости backend;
- устанавливает nginx и `envsubst`;
- копирует frontend build в `/app/frontend/dist`;
- запускает `/app/start_render.sh`.

`render/start_render.sh`:

- создаёт папки `backend/storage/projects`, `backend/storage/outputs`, `backend/storage/uploads`;
- создаёт `users.json` из переменных окружения или из `users.example.json`;
- запускает FastAPI на `127.0.0.1:8000`;
- подставляет `PORT` в nginx template;
- запускает nginx в foreground-режиме.

nginx:

- отдаёт React frontend;
- проксирует `/api/` на `http://127.0.0.1:8000/api/`;
- поддерживает скачивание Excel через `/api/download/`;
- поддерживает React history fallback через `index.html`.

## 5. Как открыть сайт

После успешного деплоя Render покажет публичную ссылку вида:

```text
https://construction-budget-agent-v3.onrender.com
```

Откройте ссылку в браузере. Приложение должно показать страницу входа.

Проверка API:

```text
https://construction-budget-agent-v3.onrender.com/api/health
```

## 6. Ограничения Render Free

Render Free подходит для демо и проверки коллегами, но не для постоянного хранения данных.

Важно:

- бесплатный сервис засыпает примерно после 15 минут простоя;
- первый запуск после сна может быть медленным;
- файлы внутри бесплатного контейнера непостоянные;
- история проектов и Excel-файлы могут пропасть после перезапуска или redeploy;
- Excel-модель нужно скачивать сразу после расчёта;
- для боевого использования нужна постоянная база данных или внешнее хранилище.

## 7. Локальные проверки

Backend:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Frontend:

```powershell
cd frontend
npm run build
```

Локальная проверка Render Dockerfile:

```powershell
docker build -f Dockerfile.render -t construction-budget-agent-render .
docker run --rm -p 10000:10000 -e PORT=10000 -e APP_ADMIN_USERNAME=admin -e APP_ADMIN_PASSWORD=admin123 construction-budget-agent-render
```

После запуска откройте:

```text
http://localhost:10000
```
