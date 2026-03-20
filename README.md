# Telegram Photo Bot MVP

Telegram bot MVP built with `Python 3.11`, `aiogram 3`, `SQLAlchemy`, Telegram Stars payments, and a pluggable image editing layer.

## Preview

| Input | Output | Logo |
|------|--------|------|
| ![](./assets/input.png) | ![](./assets/output.png) | ![](./assets/logo.png) |

## What it does

- gives every new user `5` free edits;
- accepts photos in Telegram;
- supports prompt preview mode for analysis and prompt-debugging;
- supports real image editing through `fal-ai/flux-2/klein/9b/edit`;
- stores users, generations, payments, and idempotency records;
- uses Telegram Stars as the only payment method.
- supports both local SQLite and external PostgreSQL.

## Local run

1. Create `.env` from `.env.example`
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Start the bot:

```bash
python -m app.main
```

## Railway deploy

This project is ready to deploy to Railway with the root `Dockerfile`.

Railway automatically detects and uses a root `Dockerfile` during deployment, and for Dockerfile-based services the start command defaults to the image `CMD`.

For this bot, the container start command is:

```bash
python -m app.main
```

Recommended Railway setup:

- deploy the repo as a service from GitHub;
- let Railway build from the existing `Dockerfile`;
- do not generate a public domain, because this bot uses polling;
- use your external PostgreSQL database from Supabase;
- set a restart policy so the bot comes back up automatically if it crashes.

Required Railway variables:

- `TELEGRAM_BOT_TOKEN`
- `AI_API_KEY`
- `AI_API_URL=https://queue.fal.run`
- `AI_MODEL_NAME=fal-ai/flux-2/klein/9b/edit`
- `PAYMENT_PROVIDER=telegram_stars`
- `DATABASE_URL=postgresql+asyncpg://...`
- `TEMP_DIR=/app/temp`
- `FREE_CREDITS_ON_START=5`
- `PACKAGE_PRICE_STARS=350`
- `PACKAGE_CREDITS=50`
- `MAX_PHOTO_SIZE_BYTES=10485760`
- `MAX_CONCURRENT_GENERATIONS_PER_USER=1`
- `MAX_CONCURRENT_GENERATIONS_GLOBAL=2`
- `FLOOD_WINDOW_SECONDS=2`
- `TEMP_FILE_TTL_HOURS=24`
- `USE_MOCK_AI_PROVIDER=false`
- `PROMPT_PREVIEW_MODE=false`
- `FAL_POLL_INTERVAL_SECONDS=1.5`
- `FAL_TIMEOUT_SECONDS=180`

Deploy flow:

1. Push this repository to GitHub.
2. In Railway, choose `New Project` -> `Deploy from GitHub repo`.
3. Select this repository.
4. Railway will build it from the root `Dockerfile`.
5. Add the environment variables listed above.
6. Redeploy the service.
7. Open the Railway logs and confirm the bot starts polling successfully.

## Environment variables

- `TELEGRAM_BOT_TOKEN`
- `AI_API_KEY`
- `AI_API_URL`
- `AI_MODEL_NAME`
- `PAYMENT_PROVIDER`
- `DATABASE_URL`
- `TEMP_DIR`
- `FREE_CREDITS_ON_START`
- `PACKAGE_PRICE_STARS`
- `PACKAGE_CREDITS`
- `MAX_PHOTO_SIZE_BYTES`
- `FLOOD_WINDOW_SECONDS`
- `MAX_CONCURRENT_GENERATIONS_GLOBAL`
- `TEMP_FILE_TTL_HOURS`
- `USE_MOCK_AI_PROVIDER`
- `PROMPT_PREVIEW_MODE`
- `FAL_POLL_INTERVAL_SECONDS`
- `FAL_TIMEOUT_SECONDS`

## External database

For local development, SQLite is fine:

```env
DATABASE_URL=sqlite+aiosqlite:///./data/app.db
```

For production, use PostgreSQL. Example for Supabase:

```env
DATABASE_URL=postgresql+asyncpg://postgres:YOUR_PASSWORD@db.YOUR_PROJECT.supabase.co:5432/postgres
```

The app creates tables automatically on startup, so no extra migration step is required for the first deploy.

## Telegram Stars payments

- `/buy` shows one package only;
- the bot sends a Telegram invoice in `XTR`;
- Telegram handles checkout inside the app;
- after `successful_payment`, the bot applies credits automatically;
- duplicate credit application is blocked by payment id tracking.

## fal.ai integration

To use `fal-ai/flux-2/klein/9b/edit`:

- set `USE_MOCK_AI_PROVIDER=false`
- set `PROMPT_PREVIEW_MODE=false`
- set `AI_API_KEY` to your fal key
- keep `AI_API_URL=https://queue.fal.run`
- keep `AI_MODEL_NAME=fal-ai/flux-2/klein/9b/edit`

The app will:

- convert the local Telegram image into a data URI
- submit the request to fal queue API
- poll for the result
- download the generated image
- send it back to the user

## Notes

- polling is used for the MVP;
- tables are created automatically at startup;
- SQLite is fine for local development;
- temporary files are cleaned periodically;
- at most `2` generations are sent to the AI provider at the same time by default;
- prompt preview mode is useful for debugging prompt-building before real image generation.
