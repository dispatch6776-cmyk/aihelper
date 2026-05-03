# Telegram AI Bot 🤖

A Telegram bot powered by **Claude** (chat) and **DALL-E 3** (image generation).

---

## Features

| Command | Description |
|---|---|
| Just type anything | Chat with Claude AI (remembers your conversation) |
| `/image <prompt>` | Generate an AI image using DALL-E 3 |
| `/reset` | Clear your conversation history |
| `/help` | Show the help message |

---

## Setup Guide

### Step 1 — Get a Telegram Bot Token

1. Open Telegram and search for **@BotFather**
2. Send `/newbot`
3. Choose a name (e.g. `My AI Assistant`)
4. Choose a username ending in `bot` (e.g. `myaihelper_bot`)
5. BotFather will give you a token like `7123456789:AAF...` — **copy it**

---

### Step 2 — Get your API Keys

**Anthropic (Claude)**
1. Go to https://console.anthropic.com/
2. Click **API Keys** → **Create Key**
3. Copy the key (starts with `sk-ant-...`)

**OpenAI (DALL-E 3)**
1. Go to https://platform.openai.com/api-keys
2. Click **Create new secret key**
3. Copy the key (starts with `sk-...`)

---

### Step 3 — Configure the bot

1. Copy `.env.example` and rename it to `.env`
2. Open `.env` and fill in your keys:

```
TELEGRAM_BOT_TOKEN=7123456789:AAF...
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
```

To restrict the bot to only yourself:
1. Message **@userinfobot** on Telegram to get your numeric user ID
2. Add it to `.env`:
```
ALLOWED_USER_IDS=123456789
```
Multiple users: `ALLOWED_USER_IDS=123456789,987654321`

---

### Step 4 — Install Python & dependencies

Make sure you have **Python 3.10+** installed. In VS Code:

1. Open the project folder in VS Code
2. Open the Terminal (`Ctrl + `` ` ``)
3. Run:

```bash
pip install -r requirements.txt
```

---

### Step 5 — Run the bot

In the VS Code terminal:

```bash
python bot.py
```

You should see:
```
INFO - Bot is starting…
```

Now open Telegram, find your bot, and send `/start`!

---

## File Structure

```
├── bot.py              ← Main bot code
├── requirements.txt    ← Python dependencies
├── .env                ← Your API keys (never share this!)
├── .env.example        ← Template for .env
└── README.md           ← This file
```

---

## Notes

- The bot keeps the last **20 messages** of conversation history per user. Use `/reset` to clear it.
- Images are generated at **1024×1024** resolution using DALL-E 3.
- The bot uses **claude-opus-4-6** for the best chat quality. You can change the model in `bot.py` by editing the `CLAUDE_MODEL` variable.
- Keep your `.env` file private — never commit it to Git.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `TELEGRAM_BOT_TOKEN is not set` | Make sure you have a `.env` file (not just `.env.example`) |
| Bot doesn't respond | Check the terminal for error messages |
| Image generation fails | Verify your OpenAI account has credits |
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` again |
