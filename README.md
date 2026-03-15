# Telegram AI Photo Bot MVP

Telegram bot MVP built with `Python 3.11`, `aiogram 3`, `SQLite`, `SQLAlchemy`, Telegram Stars payments, and a pluggable AI editing layer.

## What it does

- gives every new user `5` free edits;
- accepts photos in Telegram;
- supports prompt preview mode for analysis and prompt-debugging;
- supports real image editing through `fal-ai/flux-2/klein/9b/edit`;
- stores users, generations, payments, and idempotency records;
- uses Telegram Stars as the only payment method.

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
- `TEMP_FILE_TTL_HOURS`
- `USE_MOCK_AI_PROVIDER`
- `PROMPT_PREVIEW_MODE`
- `FAL_POLL_INTERVAL_SECONDS`
- `FAL_TIMEOUT_SECONDS`

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
- prompt preview mode is useful for debugging prompt-building before real image generation.
