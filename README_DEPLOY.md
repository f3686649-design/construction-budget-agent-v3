# Внедрение Construction Budget Agent v3

## 1. Первый запуск локально

Установите зависимости и запустите приложение:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\run_local.ps1
```

После запуска откройте:

```text
http://localhost:8501
```

## 2. Пользователи и пароли

Пользователи хранятся в файле:

```text
users.json
```

Пароли нельзя хранить открытым текстом. Чтобы создать хэш пароля:

```powershell
.\.venv\Scripts\python.exe -c "from backend.auth import hash_password; print(hash_password('НОВЫЙ_ПАРОЛЬ'))"
```

Добавьте пользователя в `users.json`:

```json
{
  "users": [
    {
      "login": "ivan",
      "password_hash": "pbkdf2_sha256$...",
      "role": "user"
    }
  ]
}
```

Роли:

- `admin`: администратор.
- `user`: обычный пользователь.

## 3. Запуск в офисной сети

Запустите приложение на компьютере, который будет сервером:

```powershell
.\run_local.ps1
```

Приложение будет доступно на порту `8501`.

## 4. Как узнать IP сервера

В PowerShell выполните:

```powershell
ipconfig
```

Найдите IPv4-адрес в активном сетевом адаптере, например:

```text
192.168.1.25
```

Ссылка для коллег:

```text
http://192.168.1.25:8501
```

## 5. Как открыть порт в Windows Firewall

Запустите PowerShell от имени администратора:

```powershell
New-NetFirewallRule -DisplayName "Construction Budget Agent v3" -Direction Inbound -Protocol TCP -LocalPort 8501 -Action Allow
```

Если нужно закрыть доступ:

```powershell
Remove-NetFirewallRule -DisplayName "Construction Budget Agent v3"
```

## 6. Запуск через Docker

Создайте `.env` из примера:

```powershell
Copy-Item .env.example .env
```

Запустите контейнер:

```powershell
docker compose up --build -d
```

Откройте:

```text
http://localhost:8501
```

Остановить:

```powershell
docker compose down
```

## 7. Где хранятся файлы

Excel-файлы:

```text
backend/storage/outputs
```

История проектов и metadata:

```text
backend/storage/projects
```

Каждый расчёт сохраняется в отдельной папке с `metadata.json` и копией Excel-файла.

## 8. Резервная копия

Рекомендуется регулярно копировать:

```text
users.json
backend/storage/outputs
backend/storage/projects
```

Пример резервной копии:

```powershell
$Date = Get-Date -Format "yyyyMMdd_HHmm"
New-Item -ItemType Directory -Force -Path ".\backup\$Date"
Copy-Item ".\users.json" ".\backup\$Date\users.json"
Copy-Item ".\backend\storage\outputs" ".\backup\$Date\outputs" -Recurse
Copy-Item ".\backend\storage\projects" ".\backup\$Date\projects" -Recurse
```

## 9. Проверка перед запуском для коллег

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Если тесты проходят, приложение готово к демонстрации и внутреннему использованию.
