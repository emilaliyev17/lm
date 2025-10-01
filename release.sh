#!/usr/bin/env bash
set -o errexit

echo "Running migrations..."
python manage.py migrate --no-input
echo "Migrations completed successfully!"

