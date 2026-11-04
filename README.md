# Cambridge Past Papers Bot

Telegram bot for searching and sending Cambridge past papers.

## Deploy to Render

This repository includes a Render Blueprint (`render.yaml`) for a free web
service. The bot uses Telegram long polling and exposes `/health` so Render can
check that the process is running.

1. Create a **private** GitHub repository and push this project.
2. In Render, choose **New → Blueprint** and connect the repository.
3. During setup, enter `BOT_TOKEN` as a secret environment variable. Do not put
   the token in this repository. Since the previous token was exposed, revoke it
   with BotFather and enter the newly generated token.
4. Deploy the Blueprint and wait for the service to become healthy.
5. To reduce idle spin-down, configure an external uptime monitor to request
   `https://<your-service>.onrender.com/health` every 5 minutes.

Free Render services can sleep, restart, or be suspended when usage limits are
reached. A health check does not guarantee uninterrupted 24/7 availability;
monitoring requests consume the workspace's free instance hours.

The local SQLite database is ephemeral on Render's free service. The bot can
re-fetch and re-upload papers if its Telegram file-ID cache is lost, but cached
file IDs and saved subject favorites may be lost after a restart or redeploy.
