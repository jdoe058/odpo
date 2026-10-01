#!/bin/bash
set -e
cd /home/sa/odpo_prod
source venv/bin/activate
git pull
pip install -r requirements.txt
python manage.py migrate --noinput
python manage.py collectstatic --noinput
sudo systemctl restart gunicorn
echo "Deploy OK"