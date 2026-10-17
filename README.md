# DiamondBot

A Persian-language Telegram bot for educational advising: student registration,
referral links, product purchases through ZarinPal or an operator, advisor chats,
admin notifications, customer spreadsheet exports, and student PDF upload/retrieval.
Existing business branding, public links, and the about-us photo are preserved.

## Stack

Python 3.12, python-telegram-bot 21.4, PostgreSQL 15, Prisma Client Python,
FastAPI/Uvicorn, and Docker Compose. Dependencies are pinned in `requirements.txt`;
the database schema and migrations are in `prisma/`.

## Development

Run commands from the repository root. Use a dedicated development Telegram bot
and test payment credentials, never production credentials.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.sample .env
docker compose -f docker-compose.dev.yml up -d
prisma generate
prisma migrate deploy
mkdir -p logs
python main.py
```

Before starting the bot, edit `.env` and set `BOT_TOKEN`. The sample selects
`MODE=development` (polling) and matches the development PostgreSQL container:
database `diamond`, user/password `admin`, host `localhost`, port `6000`.
These are public local-development defaults, not production credentials. The
development Compose file starts only PostgreSQL, not the bot or verification API.
Prisma and `main.py` load `.env`; keep it out of version control.

## Configuration

| Variable | Purpose |
| --- | --- |
| `BOT_TOKEN` | Telegram token for local runs; production reads `bot_token.txt`. |
| `MODE` | `development` for polling or `production` for webhooks. The Docker image sets `production`. |
| `DATABASE_URL` | PostgreSQL connection URL for Prisma and local processes; `.env.sample` constructs it from `DB`, `DB_USER`, `DB_PASS`, `DB_HOST`, and `DB_PORT`. |
| `ZARINPAL_MERCHANT_ID` | Merchant identifier required for ZarinPal payments and production Compose. |
| `WEBHOOK_HOST` | Public hostname only, without scheme, port, or path; required in production. |
| `WEBHOOK_PORT` | HTTPS URL port and bot listener port; defaults to `8443`. Use a Telegram-supported webhook port. |
| `ZARINLINK_PHONE_NUMBER` | Optional legacy payment-account login phone number. |
| `ZARINLINK_PAYMENT_LINK` | Optional legacy public payment link. |
| `ZARINLINK_PAYMENTS_URL` | Optional legacy merchant-dashboard payments URL. |

## Production

Create four local, ignored files containing only their respective values:
`db.txt` (database name), `db_user.txt`, `db_pass.txt`, and `bot_token.txt`.
Restrict their filesystem permissions and use strong, unique production values.
Also set `WEBHOOK_HOST`, `WEBHOOK_PORT`, and `ZARINPAL_MERCHANT_ID` in `.env`
or the shell environment. Compose explicitly passes these settings and optional
legacy settings into the bot container; it does not pass local database values.

```bash
docker compose -f docker-compose.yml config --quiet
docker compose -f docker-compose.yml up --build -d
```

`run_bot.bash` reads the mounted Docker secret files, constructs `DATABASE_URL`
for the `db:5432` service, generates the Prisma client, applies migrations, and
starts `main.py`. Named volumes persist database data, bot data, and logs.
The image uses Python 3.12 and exposes port `8443`; Compose maps the configured
`WEBHOOK_PORT` to the same port in the container. The bot listens on `0.0.0.0`
and registers `https://WEBHOOK_HOST:WEBHOOK_PORT` with Telegram.

Provide public DNS and a trusted HTTPS reverse proxy/load balancer forwarding
to that listener. The bot does not configure a TLS certificate itself. Ensure
the advertised port is supported by Telegram and reachable from Telegram's
servers. Restrict direct access to the unencrypted backend listener.

## Verification API

`webserver.py` is a separate FastAPI entry point exposing
`GET /verify/{order_id}?bot_username=...`. Neither Compose file starts it.
With dependencies, generated Prisma client, migrations, and the appropriate
database/payment environment configured, run it separately:

```bash
python webserver.py
```

This loads `.env` and binds Uvicorn to `127.0.0.1:8000`. For an explicitly
configured service listener, use `uvicorn webserver:app --host 0.0.0.0 --port 8000`.
Provide HTTPS routing and ensure the payment callback targets the deployed
endpoint; starting the Telegram bot does not deploy or route this API.


