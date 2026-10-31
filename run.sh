#!/usr/bin/env bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "=========================================================="
echo " Starting Yrys Kanban Platform (Backend & Frontend)"
echo " Clean Architecture + DDD + DI + UoW | Next.js 16 + Django"
echo "=========================================================="

# 1. Start Django Backend on port 8080
if ss -tulpn | grep -q ":8080 "; then
    echo "Backend already running on http://127.0.0.1:8080"
else
    echo "Starting Backend server on http://127.0.0.1:8080..."
    nohup backend/venv/bin/python backend/manage.py runserver 127.0.0.1:8080 > backend.log 2>&1 &
    sleep 2
fi

# 2. Start Next.js Frontend on port 3001
if ss -tulpn | grep -q ":3001 "; then
    echo "Frontend already running on http://localhost:3001"
else
    echo "Starting Frontend server on http://localhost:3001..."
    cd frontend
    nohup npx next start -p 3001 > ../frontend.log 2>&1 &
    cd ..
    sleep 2
fi

echo ""
echo "🚀 Everything is up and running!"
echo "👉 Frontend URL: http://localhost:3001"
echo "👉 Backend API:  http://127.0.0.1:8080/api"
echo ""
echo "Аккаунт для входа:"
echo "👑 Генеральный директор: admin@gmail.com / admin12345"
echo "=========================================================="
