#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input
# Миграции временно отключены - запустим их вручную после деплоя
# python manage.py migrate --no-input
