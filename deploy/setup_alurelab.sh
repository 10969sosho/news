#!/bin/bash
# ==============================================================================
# Skrip Deployment Anti-Hoax AI ke Hosting Alurelab
# Server: emerald.hidden-server.net:31988 (User: alurelab)
#
# SOP ALURELAB:
# 1. Folder ~/repositories/$namaproject HANYA untuk git pull source code bersih.
# 2. DILARANG run install / build di ~/repositories/.
# 3. Seluruh dependensi, build, dan env HANYA dilakukan di path domain tujuan!
# ==============================================================================

set -e

# Konfigurasi variabel untuk news.solusisurabaya.com
PROJECT_NAME="news"
DOMAIN_TARGET="news.solusisurabaya.com"
TARGET_DIR="/home/alurelab/$DOMAIN_TARGET"
REPO_DIR="/home/alurelab/repositories/$PROJECT_NAME"

echo "=== [1/6] Sinkronisasi Git di Repository ==="
if [ -d "$REPO_DIR" ]; then
    cd "$REPO_DIR"
    git pull origin main
else
    echo "Peringatan: Direktori $REPO_DIR belum ada. Pastikan git clone dilakukan terlebih dahulu."
    exit 1
fi

echo "=== [2/6] Backup & Copy ke Direktori Domain Target ==="
mkdir -p "$TARGET_DIR"

# Buat backup file .env jika ada di folder target
if [ -f "$TARGET_DIR/.env" ]; then
    cp "$TARGET_DIR/.env" "$TARGET_DIR/.env.bak"
fi

# Salin source code bersih ke direktori domain target
rsync -av --exclude='.git' --exclude='node_modules' --exclude='venv' "$REPO_DIR/" "$TARGET_DIR/"

# Kembalikan .env yang ada
if [ -f "$TARGET_DIR/.env.bak" ]; then
    mv "$TARGET_DIR/.env.bak" "$TARGET_DIR/.env"
fi

echo "=== [3/6] Setup Lingkungan Python (Backend) di Target ==="
cd "$TARGET_DIR/backend"

# Deteksi binary Python
if command -v python3 &> /dev/null; then
    PY_BIN="python3"
elif [ -f "/opt/alt/python310/bin/python3" ]; then
    PY_BIN="/opt/alt/python310/bin/python3"
elif [ -f "/opt/alt/python311/bin/python3" ]; then
    PY_BIN="/opt/alt/python311/bin/python3"
else
    echo "Error: Python 3 tidak ditemukan di sistem."
    exit 1
fi

if [ ! -d "venv" ]; then
    "$PY_BIN" -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "=== [4/6] Setup Lingkungan Node.js & Build (Frontend) di Target ==="
cd "$TARGET_DIR/frontend"
npm install
npm run build

echo "=== [5/6] Jalankan Service via PM2 ==="
cd "$TARGET_DIR"
if command -v pm2 &> /dev/null; then
    pm2 start deploy/ecosystem.config.js || pm2 restart deploy/ecosystem.config.js
    pm2 save
    echo "Aplikasi berhasil dijalankan di PM2."
else
    echo "PM2 tidak ditemukan. Menjalankan via background task biasa."
fi

echo "=== [6/6] Deployment Selesai! ==="
echo "Backend berjalan di http://127.0.0.1:8000"
echo "Frontend berjalan di http://127.0.0.1:3000"
echo "Pastikan reverse proxy Nginx / Apache diarahkan ke port 3000."
