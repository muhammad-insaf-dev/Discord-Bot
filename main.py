import os
import threading

from flask import Flask
import discord

app = Flask(__name__)


@app.route("/")
def home():
    return "Discord bot is running!", 200


@app.route("/health")
def health():
    return "OK", 200


def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)


@client.event
async def on_ready():
    print(f"Logged in as {client.user}")


@client.event
async def on_message(message):
    if message.author.bot:
        return

    if message.content.lower().strip() == "hi":
        await message.channel.send("hi")


if __name__ == "__main__":
    token = os.environ.get("DISCORD_TOKEN")

    if not token:
        raise RuntimeError("DISCORD_TOKEN environment variable is not set.")

    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()

    client.run(token)
