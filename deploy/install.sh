#!/usr/bin/env bash
# Deploy SorteZeferius na Raspberry Pi (porta 2525, nginx isolado).
# Uso: sudo bash deploy/install.sh   (rodar a partir da raiz do projeto)
set -euo pipefail

APP_DIR=/opt/sortezeferius
WEB_DIR=/var/www/sortezeferius
SRC_DIR="$(cd "$(dirname "$0")/.." && pwd)"
RUN_USER="${SUDO_USER:-pi}"

echo ">> Verificando porta interna 8025 e 2525..."
if ss -ltn | grep -q ':8025 ' && ! systemctl is-active --quiet sortezeferius; then
  echo "ERRO: porta 8025 já em uso por outro serviço. Edite a porta em deploy/systemd e deploy/nginx."; exit 1
fi
if ss -ltn | grep -q ':2525 ' && [ ! -f /etc/nginx/sites-enabled/sorte.zeferius.com.br.conf ]; then
  echo "ERRO: porta 2525 já em uso por outro serviço."; exit 1
fi

echo ">> Backend"
mkdir -p "$APP_DIR/backend"
cp "$SRC_DIR/backend/server.py" "$APP_DIR/backend/"
[ -f "$APP_DIR/backend/.env" ] || cp "$SRC_DIR/deploy/backend.env.production" "$APP_DIR/backend/.env"
[ -d "$APP_DIR/venv" ] || python3 -m venv "$APP_DIR/venv"
"$APP_DIR/venv/bin/pip" install -q --upgrade pip
"$APP_DIR/venv/bin/pip" install -q -r "$SRC_DIR/deploy/requirements-pi.txt"
chown -R "$RUN_USER":"$RUN_USER" "$APP_DIR"

sed "s/^User=.*/User=$RUN_USER/" "$SRC_DIR/deploy/systemd/sortezeferius.service" > /etc/systemd/system/sortezeferius.service
systemctl daemon-reload
systemctl enable sortezeferius
systemctl restart sortezeferius

echo ">> Frontend"
mkdir -p "$WEB_DIR"
if [ -f "$SRC_DIR/deploy/frontend-build/index.html" ] && [ "${REBUILD:-0}" != "1" ]; then
  echo "   usando build pronto (deploy/frontend-build). Para recompilar: sudo REBUILD=1 bash deploy/install.sh"
  rsync -a --delete "$SRC_DIR/deploy/frontend-build/" "$WEB_DIR/"
else
  cd "$SRC_DIR/frontend"
  sudo -u "$RUN_USER" yarn install --frozen-lockfile || sudo -u "$RUN_USER" yarn install
  sudo -u "$RUN_USER" env REACT_APP_BACKEND_URL="" GENERATE_SOURCEMAP=false NODE_OPTIONS=--max-old-space-size=1536 yarn build
  rsync -a --delete build/ "$WEB_DIR/"
fi
chown -R www-data:www-data "$WEB_DIR" 2>/dev/null || true

echo ">> Nginx (arquivo próprio, sem tocar nos outros sites)"
cp "$SRC_DIR/deploy/nginx/sorte.zeferius.com.br.conf" /etc/nginx/sites-available/sorte.zeferius.com.br.conf
ln -sf /etc/nginx/sites-available/sorte.zeferius.com.br.conf /etc/nginx/sites-enabled/sorte.zeferius.com.br.conf
if nginx -t; then
  systemctl reload nginx   # reload = sem derrubar os outros sites
else
  echo "ERRO na config do nginx - removendo o link para não afetar outros sites"
  rm -f /etc/nginx/sites-enabled/sorte.zeferius.com.br.conf
  exit 1
fi

sleep 2
curl -fsS http://127.0.0.1:2525/api/ && echo && echo ">> OK! Acesse http://sorte.zeferius.com.br:2525"
