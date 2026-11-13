import os
import random
import threading

from flask import Flask
import discord
from openai import AsyncOpenAI

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

# OpenAI is enabled when OPENAI_API_KEY is configured in Render.
openai_client = (
    AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])
    if os.environ.get("OPENAI_API_KEY")
    else None
)
ai_histories = {}
AI_MODEL = "gpt-4.1-mini"
AI_SYSTEM_PROMPT = (
    "You are a friendly, helpful Discord assistant. "
    "You can understand and reply in Malayalam, Manglish, English, and other languages. "
    "Reply in the language the user uses. Keep replies clear and concise."
)

# One active number game per Discord channel.
number_games = {}
MAX_TRIES = 3
MIN_NUMBER = 1
MAX_NUMBER = 10


async def send_long_message(channel, text):
    # Discord messages have a 2000-character limit.
    for start in range(0, len(text), 1900):
        await channel.send(text[start:start + 1900])


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

    if command == "!aireset":
        ai_histories.pop((message.channel.id, message.author.id), None)
        await message.channel.send("🧹 Your AI chat history has been cleared.")
        return

    if command == "!ai" or command.startswith("!ai "):
        if openai_client is None:
            await message.channel.send(
                "⚙️ AI chat is not configured yet. The bot owner must add "
                "OPENAI_API_KEY in Render Environment settings."
            )
            return

        prompt = content[3:].strip()
        if not prompt:
            await message.channel.send(
                "Ask me something! Example: `!ai കേരളത്തിന്റെ തലസ്ഥാനം ഏതാണ്?`"
            )
            return

        history_key = (message.channel.id, message.author.id)
        history = ai_histories.setdefault(
            history_key, [{"role": "system", "content": AI_SYSTEM_PROMPT}]
        )
        history.append({"role": "user", "content": prompt})
        # Keep the system prompt and the latest 12 conversation messages.
        history[:] = [history[0]] + history[-12:]

        async with message.channel.typing():
            try:
                response = await openai_client.chat.completions.create(
                    model=AI_MODEL,
                    messages=history,
                    max_tokens=500,
                )
                answer = response.choices[0].message.content or "I couldn't create a reply."
                history.append({"role": "assistant", "content": answer})
                await send_long_message(message.channel, answer)
            except Exception:
                # Do not expose API keys or internal error details in Discord.
                if history and history[-1]["role"] == "user":
                    history.pop()
                await message.channel.send(
                    "⚠️ AI reply failed. Please try again in a moment."
                )
        return


if __name__ == "__main__":
    token = os.environ.get("DISCORD_TOKEN")

    if not token:
        raise RuntimeError("DISCORD_TOKEN environment variable is not set.")

    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()

    client.run(token)
