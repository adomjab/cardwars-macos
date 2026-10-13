#!/usr/bin/env bash
# Install or update the Card Wars server on a Debian/Ubuntu machine.
# Run on the server (e.g. in Google Cloud's SSH window):
#   curl -fsSL https://raw.githubusercontent.com/adomjab/cardwars-macos/dev/server/install.sh | sudo bash
# Re-running it updates the server program and keeps all accounts and saves.
set -euo pipefail

REPO_RAW="https://raw.githubusercontent.com/adomjab/cardwars-macos/dev/server"
APP_DIR=/opt/cardwars
DATA_DIR=/var/lib/cardwars
PORT="${CARDWARS_PORT:-80}"

if [ "$(id -u)" -ne 0 ]; then
  echo "Please run with sudo." >&2
  exit 1
fi

echo "==> Checking for Python 3"
if ! command -v python3 >/dev/null 2>&1; then
  apt-get update -q && apt-get install -y -q python3
fi

echo "==> Creating the cardwars user and folders"
id cardwars >/dev/null 2>&1 || useradd --system --home "$DATA_DIR" --shell /usr/sbin/nologin cardwars
mkdir -p "$APP_DIR" "$DATA_DIR"
chown cardwars:cardwars "$DATA_DIR"

echo "==> Downloading the server program"
curl -fsSL "$REPO_RAW/cardwars_server.py" -o "$APP_DIR/cardwars_server.py.new"
python3 -m py_compile "$APP_DIR/cardwars_server.py.new"
mv "$APP_DIR/cardwars_server.py.new" "$APP_DIR/cardwars_server.py"

echo "==> Setting it up to run automatically"
cat > /etc/systemd/system/cardwars.service <<EOF
[Unit]
Description=Card Wars server
After=network-online.target
Wants=network-online.target

[Service]
User=cardwars
Group=cardwars
WorkingDirectory=$DATA_DIR
ExecStart=/usr/bin/python3 $APP_DIR/cardwars_server.py --port $PORT --db $DATA_DIR/cardwars.db
AmbientCapabilities=CAP_NET_BIND_SERVICE
Restart=always
RestartSec=3
NoNewPrivileges=true
ProtectSystem=strict
ReadWritePaths=$DATA_DIR
ProtectHome=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable cardwars >/dev/null 2>&1
systemctl restart cardwars
sleep 2

if systemctl is-active --quiet cardwars && curl -fsS "http://127.0.0.1:$PORT/" >/dev/null; then
  IP="$(curl -fsS -H 'Metadata-Flavor: Google' \
    http://metadata.google.internal/computeMetadata/v1/instance/network-interfaces/0/access-configs/0/external-ip 2>/dev/null || true)"
  echo
  echo "==> Card Wars server is running!"
  if [ -n "$IP" ]; then
    echo "    Address for server_settings.json:  http://$IP/"
  fi
  echo "    Status:  sudo systemctl status cardwars"
  echo "    Logs:    sudo journalctl -u cardwars -f"
  echo "    Data:    $DATA_DIR/cardwars.db"
else
  echo "The server did not start. Recent logs:" >&2
  journalctl -u cardwars -n 30 --no-pager >&2 || true
  exit 1
fi
