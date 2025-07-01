#!/bin/bash
set -e

# Basic system dependencies
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip postgresql git build-essential

# PostgreSQL setup
sudo -u postgres psql -c "CREATE USER kmg_user WITH PASSWORD 'password';" || true
sudo -u postgres psql -c "CREATE DATABASE kmg_autotrader OWNER kmg_user;" || true

python3 -m venv venv
. venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "Copy .env.example to .env and set credentials."
python main.py
