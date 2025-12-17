#!/bin/bash
set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

log() {
    printf "${BLUE}[INFO] %s${NC}\n" "$1"
}

error() {
    printf "${RED}[ERROR] %s${NC}\n" "$1"
}

success() {
    printf "${GREEN}[SUCCESS] %s${NC}\n" "$1"
}

log "[1/5] Checking Environment..."

if ! command -v docker > /dev/null 2>&1; then
    if ! docker --version > /dev/null 2>&1; then
        error "Docker not found! Please install Docker to run the XMPP server."
        printf "Debug: PATH is $PATH\n"
        exit 1
    fi
fi

if ! command -v node > /dev/null 2>&1; then
    error "Node.js not found!"
    exit 1
fi

log "[2/5] Starting XMPP Server (Prosody)..."

log "Scanning for blocking services on Port 5222..."

CONFLICT_IDS=$(docker ps -a -q --filter "publish=5222")
if [ -n "$CONFLICT_IDS" ]; then
    log "Found active Docker container(s) holding Port 5222. Removing them..."
    docker rm -f $CONFLICT_IDS > /dev/null 2>&1
fi

if ss -tulpn | grep ':5222 ' > /dev/null 2>&1 || lsof -i :5222 > /dev/null 2>&1; then
    log "Port 5222 still busy (Non-Docker). Initiating system force kill..."
    
    if command -v fuser > /dev/null 2>&1; then
        sudo fuser -k 5222/tcp > /dev/null 2>&1 || true
    elif command -v lsof > /dev/null 2>&1; then
        PID=$(lsof -t -i:5222)
        if [ -n "$PID" ]; then
            sudo kill -9 $PID || true
        fi
    else
        sudo pkill -f prosody || true
    fi
    sleep 2
fi

log "Cleaning up old target container..."
docker rm -f showcase_xmpp > /dev/null 2>&1 || true

if ss -tulpn | grep ':5222 ' > /dev/null 2>&1; then
   error "FATAL: Port 5222 is LOCKED by a zombie process or system service I cannot kill."
   log "Try running 'sudo netstat -pna | grep 5222' to inspect manually."
   exit 1
fi

log "Creating new Prosody container..."
docker run -d --restart=no --name showcase_xmpp \
    -p 5222:5222 -p 5269:5269 -p 5280:5280 \
    -e PROSODY_ADMIN=admin@localhost \
    -e PROSODY_ADMIN_PASSWORD=password \
    prosody/prosody

log "Waiting for XMPP server to initialize..."
sleep 5

log "Applying SSL Permission Fix..."
docker exec -u root showcase_xmpp chown -R prosody:prosody /etc/prosody/certs || true
docker exec showcase_xmpp prosodyctl reload > /dev/null 2>&1 || true
sleep 3

log "Registering Agents..."
docker exec showcase_xmpp prosodyctl register server localhost password || true
for i in $(seq 1 5); do
    docker exec showcase_xmpp prosodyctl register client$i localhost password || true
done

log "[3/5] Setting up Python Environment..."
cd backend
if [ ! -d "venv" ]; then
    log "Creating virtual environment..."
    python3 -m venv venv
fi
log "Installing Backend Dependencies (this may take a while)..."
log "Installing Backend Dependencies (this may take a while)..."
./venv/bin/pip install -r ../requirements.txt
cd .. 

log "[4/5] Starting Backend System..."
# Check for local nsl-kdd first, then fallback to parent
if [ -d "$(pwd)/nsl-kdd" ]; then
    export DATA_PATH="$(pwd)/nsl-kdd"
else
    export DATA_PATH="$(pwd)/../nsl-kdd"
fi
export XMPP_HOST="localhost"
export XMPP_PASS="password"

if ss -tulpn | grep ':8000 ' > /dev/null 2>&1 || lsof -i :8000 > /dev/null 2>&1; then
    log "Port 8000 is busy. Killing old backend process..."
    if command -v fuser > /dev/null 2>&1; then
        sudo fuser -k 8000/tcp > /dev/null 2>&1 || true
    else
        PID=$(lsof -t -i:8000)
        if [ -n "$PID" ]; then
            sudo kill -9 $PID || true
        fi
    fi
    sleep 1
fi

./backend/venv/bin/python -m uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

log "[5/5] Starting Frontend Interface..."
cd frontend
log "Performing clean frontend installation (fixing white screen)..."
npm install

success "System is READY! Opening Dashboard..."
npm run dev -- --open --host &
FRONTEND_PID=$!

trap "kill $BACKEND_PID $FRONTEND_PID; echo 'System Stopped'; exit" INT

wait
