# Deploy SorteZeferius na Raspberry Pi

Porta pública: **2525** (nginx) • Backend interno: **127.0.0.1:8025** • Subdomínio: **sorte.zeferius.com.br**
Nada aqui altera os outros sites: o nginx ganha um arquivo próprio e é feito `reload` (não `restart`), com `nginx -t` antes.

## 1. Pré-requisitos (uma vez)
```bash
sudo apt update && sudo apt install -y python3-venv rsync nginx
# Node 20 + yarn (se ainda não tiver)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - && sudo apt install -y nodejs && sudo npm i -g yarn
```

## 2. Usuário no MongoDB (se o Mongo é local na Raspberry)
```bash
mongosh -u <admin> -p --authenticationDatabase admin
use sortezeferiusdb
db.createUser({ user: "sortezeferiusdb", pwd: "NVOoBxx3znYTvVMM", roles: [{ role: "readWrite", db: "sortezeferiusdb" }] })
```
Se usar **MongoDB Atlas**, edite `MONGO_URL` em `/opt/sortezeferius/backend/.env` com o host do cluster.

## 3. Instalar / atualizar
```bash
git clone <seu-repo> sortezeferius && cd sortezeferius
sudo bash deploy/install.sh
```
Edite `/opt/sortezeferius/backend/.env` (troque `JWT_SECRET`) e rode `sudo systemctl restart sortezeferius`.

## 4. DNS / roteador
- Registro **A** `sorte` → IP público da sua casa (ou CNAME para seu DDNS).
- Encaminhe a porta **2525** do roteador para a Raspberry.
- Acesse: `http://sorte.zeferius.com.br:2525` — Painel: `/admin`.

## 5. Webhooks (pagamento confirmado automático)
Mercado Pago e InfinitePay exigem **HTTPS** para webhooks. Opções:
- Cloudflare (proxy laranja) com Origin Rule apontando para a porta 2525, ou
- Seu nginx principal na 443 fazendo `proxy_pass http://127.0.0.1:2525;` para este subdomínio.
Depois defina `PUBLIC_URL="https://sorte.zeferius.com.br"`.
Sem HTTPS, o pagamento ainda é confirmado por consulta (polling) enquanto o cliente está na tela, e você pode aprovar manualmente no painel.

## Comandos úteis
```bash
sudo systemctl status sortezeferius
journalctl -u sortezeferius -f
tail -f /var/log/nginx/sortezeferius.error.log
```
