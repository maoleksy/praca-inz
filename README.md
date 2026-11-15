# praca-inz

Aplikacja Flask (port 5050) + rozszerzenie przeglądarki (`extension/`, łączy się z `http://51.255.34.32:5050`).

## Wdrożenie na VPS

Serwer: `ubuntu@51.255.34.32` (klucz `~/.ssh/footspace_vps`). Spis całego serwera: `/srv/README.md`.

```bash
docker buildx build --platform linux/amd64 -t nanekx/praca-inz:latest --push .
ssh -i ~/.ssh/footspace_vps ubuntu@51.255.34.32 \
  'cd /srv/apps/praca-inz && docker compose pull && docker compose up -d'
```

| Na VPS | |
|---|---|
| Folder | `/srv/apps/praca-inz` (`compose.yaml`, projekt `praca-inz`, kontener `praca-inz-app`) |
| Sekrety | `/srv/apps/praca-inz/.env` (DB_*, BOT_TOKEN, CHAT_ID, DISCORD_WEBHOOK, SECRET_KEY) — tylko na serwerze |
| Baza | MySQL na hoście, `price_monitor` |
| Dostęp | bez domeny: kontener na 127.0.0.1:8050, z zewnątrz http://51.255.34.32:5050 przez nginx (`/srv/nginx/public-ports.conf`) |
