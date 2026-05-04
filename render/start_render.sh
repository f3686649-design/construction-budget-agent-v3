#!/usr/bin/env sh
set -eu

mkdir -p backend/storage/projects backend/storage/outputs backend/storage/uploads

if [ ! -f users.json ]; then
  if [ -n "${APP_ADMIN_USERNAME:-}" ] && [ -n "${APP_ADMIN_PASSWORD:-}" ]; then
    python - <<'PY'
import json
import os
from pathlib import Path

from backend.auth import create_user_record

username = os.environ["APP_ADMIN_USERNAME"]
password = os.environ["APP_ADMIN_PASSWORD"]
role = os.environ.get("APP_ADMIN_ROLE", "admin")

payload = {
    "users": [
        create_user_record(username=username, password=password, role=role),
    ],
}

Path("users.json").write_text(
    json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
PY
    echo "Создан users.json из переменных окружения Render."
  elif [ -f users.example.json ]; then
    cp users.example.json users.json
    echo "Создан демо users.json из users.example.json."
  else
    printf '{"users":[]}\n' > users.json
    echo "Создан пустой users.json."
  fi
fi

PORT="${PORT:-7860}"
export PORT

rm -f /etc/nginx/sites-enabled/default /etc/nginx/conf.d/default.conf
envsubst '${PORT}' < /etc/nginx/templates/default.conf.template > /etc/nginx/conf.d/default.conf

uvicorn backend.main:app --host 127.0.0.1 --port 8000 &

nginx -g "daemon off;"
