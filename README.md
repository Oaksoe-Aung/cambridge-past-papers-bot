# Cambridge Past Papers Bot

Telegram bot for searching and sending Cambridge past papers.

## Deploy to Render

The bot uses Telegram long polling and exposes `/health` so Render can check
that the process is running.

1. In Render, choose **New → Web Service** and connect this repository.
2. Set the build command to `pip install -r requirements.txt` and the start
   command to `python bot.py`.
3. Set the health check path to `/health` and select the Free instance plan.
4. Add `BOT_TOKEN` as a secret environment variable in Render. Never commit the
   token. Revoke the previously exposed token with BotFather and use its
   replacement.
5. Deploy and wait for the service to become healthy.
6. To reduce idle spin-down, configure an external uptime monitor to request
   `https://<your-service>.onrender.com/health` every 5 minutes.

Free Render services can sleep, restart, or be suspended when usage limits are
reached. A health check does not guarantee uninterrupted 24/7 availability;
monitoring requests consume the workspace's free instance hours.

The local SQLite database is ephemeral on Render's free service. The bot can
re-fetch and re-upload papers if its Telegram file-ID cache is lost, but cached
file IDs and saved subject favorites may be lost after a restart or redeploy.
