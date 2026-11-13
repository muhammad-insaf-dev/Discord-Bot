import os
import random
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

# One active number game per Discord channel.
number_games = {}
MAX_TRIES = 3
MIN_NUMBER = 1
MAX_NUMBER = 10


@client.event
async def on_ready():
    print(f"Logged in as {client.user}")


@client.event
async def on_message(message):
    if message.author.bot:
        return

    content = message.content.strip()
    command = content.lower()

    if command == "hi":
        await message.channel.send("hi")
        return

    if command in ("!predict", "!number", "!numbergame"):
        if message.channel.id in number_games:
            await message.channel.send(
                "A number game is already running here! "
                "Guess with `!guess 1` to `!guess 10`."
            )
            return

        number_games[message.channel.id] = {
            "number": random.randint(MIN_NUMBER, MAX_NUMBER),
            "tries": 0,
            "player_id": message.author.id,
        }
        await message.channel.send(
            f"🎯 **Number Prediction Game!**\n"
            f"I picked a number from **{MIN_NUMBER} to {MAX_NUMBER}**.\n"
            f"You have **{MAX_TRIES} tries**. Guess using `!guess 5`!"
        )
        return

    if command.startswith("!guess"):
        game = number_games.get(message.channel.id)
        if game is None:
            await message.channel.send("Start a game first with **!predict**.")
            return

        if message.author.id != game["player_id"]:
            await message.channel.send("This game belongs to the player who started it.")
            return

        parts = content.split()
        if len(parts) != 2:
            await message.channel.send("Use this format: **!guess 5**")
            return

        try:
            guess = int(parts[1])
        except ValueError:
            await message.channel.send("Please enter a whole number from 1 to 10.")
            return

        if not MIN_NUMBER <= guess <= MAX_NUMBER:
            await message.channel.send("Choose a number from **1 to 10**.")
            return

        game["tries"] += 1
        answer = game["number"]

        if guess == answer:
            del number_games[message.channel.id]
            await message.channel.send(
                f"🎉 **Correct!** The number was **{answer}**. "
                f"You won in **{game['tries']}** attempt(s)!"
            )
        elif game["tries"] >= MAX_TRIES:
            del number_games[message.channel.id]
            await message.channel.send(
                f"❌ Game over! The number was **{answer}**. Try again with **!predict**."
            )
        elif guess < answer:
            await message.channel.send(
                f"⬆️ Too low! Try a higher number. "
                f"**{MAX_TRIES - game['tries']} tries left.**"
            )
        else:
            await message.channel.send(
                f"⬇️ Too high! Try a lower number. "
                f"**{MAX_TRIES - game['tries']} tries left.**"
            )
        return

    if command == "!stopguess":
        game = number_games.get(message.channel.id)
        if game is None:
            await message.channel.send("There is no active number game here.")
        elif message.author.id != game["player_id"]:
            await message.channel.send("Only the player who started the game can stop it.")
        else:
            del number_games[message.channel.id]
            await message.channel.send("🛑 Number game stopped.")
        return


if __name__ == "__main__":
    token = os.environ.get("DISCORD_TOKEN")

    if not token:
        raise RuntimeError("DISCORD_TOKEN environment variable is not set.")

    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()

    client.run(token)
