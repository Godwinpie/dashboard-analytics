#!/bin/bash
set -e

echo "Step 1: Changing directory to /home/ubuntu/dashboard_charts..."
cd /home/godwinsimon145/dashboard-analytics

echo "Step 2: Activating virtual environment..."
source venv/bin/activate

echo "Step 3: Installing/updating Python dependencies inside venv..."
python -m pip install --no-cache-dir -r requirements.txt

python manage.py makemigrations
python manage.py migrate

echo "Step 4: Reloading systemd manager configuration..."
sudo systemctl daemon-reload

echo "Step 5: Restarting gunicorn service..."
sudo systemctl restart gunicorn
sudo systemctl restart nginx

echo "Deployment script completed successfully."
