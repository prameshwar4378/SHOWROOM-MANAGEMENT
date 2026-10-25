#!/usr/bin/env bash
# ====================================================================
# Tractor Showroom Management System — Automated Production Deployment
# Usage:
#   chmod +x deploy/deploy.sh
#   ./deploy/deploy.sh
# ====================================================================

set -e

echo "🚀 [1/6] Pulling latest updates from GitHub (main)..."
git pull origin main

echo "📦 [2/6] Activating virtual environment & installing dependencies..."
if [ -d "../venv" ]; then
    source ../venv/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "⚠️  No virtualenv found. Creating virtualenv 'venv'..."
    python3 -m venv venv
    source venv/bin/activate
fi

pip install --upgrade pip
pip install -r requirements.txt

echo "🗄️  [3/6] Running database migrations..."
python manage.py migrate --noinput

echo "🎨 [4/6] Collecting static assets (WhiteNoise & Nginx)..."
python manage.py collectstatic --noinput

echo "🔍 [5/6] Verifying Django deployment security checklist..."
python manage.py check --deploy

echo "🔄 [6/6] Reloading Gunicorn and WhatsApp Bridge services..."
if command -v systemctl >/dev/null 2>&1; then
    sudo systemctl restart showroom || echo "⚠️ showroom systemd service not found, skipping restart."
    sudo systemctl restart showroom-whatsapp || echo "⚠️ showroom-whatsapp systemd service not found, skipping restart."
    echo "✅ Gunicorn and WhatsApp Bridge reloaded successfully!"
else
    echo "ℹ️  Non-systemd environment. Please restart your application server manually."
fi

echo "===================================================================="
echo "🎉 DEPLOYMENT COMPLETE! Showroom Management is live and running."
echo "===================================================================="
