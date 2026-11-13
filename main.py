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

# Simple built-in chat replies. No AI/API key or paid service required.
CHAT_REPLIES = [
    (("hi", "hello", "hey", "ഹായ്", "ഹലോ"), "ഹായ്! 😊 സുഖമാണോ? എന്ത് സഹായമാണ് വേണ്ടത്?"),
    (("how are you", "how r u", "സുഖമാണോ", "സുഖം ആണോ"), "എനിക്ക് സുഖം തന്നെ! 😄 നിങ്ങളോ?"),
    (("welcome", "സ്വാഗതം"), "നന്ദി! 💛 നിങ്ങളെയും സ്വാഗതം ചെയ്യുന്നു!"),
    (("good morning", "ഗുഡ് മോർണിംഗ്"), "Good morning! ☀️ ഇന്നത്തെ ദിവസം സന്തോഷകരമാകട്ടെ!"),
    (("good afternoon",), "Good afternoon! 😊 ദിവസം നന്നായി പോകുന്നുണ്ടോ?"),
    (("good evening",), "Good evening! 🌆 സുഖമാണോ?"),
    (("good night", "ഗുഡ് നൈറ്റ്"), "Good night! 🌙 നന്നായി ഉറങ്ങൂ!"),
    (("thank you", "thanks", "നന്ദി", "താങ്ക്സ്"), "You're welcome! 😊 വേറെ എന്തെങ്കിലും സഹായം വേണോ?"),
    (("bye", "goodbye", "പോയിട്ട് വരാം", "ബൈ"), "ശരി, വീണ്ടും കാണാം! 👋 സൂക്ഷിക്കണേ!"),
    (("your name", "who are you", "നിന്റെ പേര്", "ആരാണ് നീ"), "ഞാൻ നിങ്ങളുടെ Discord Bot ആണ്! 🤖"),
    (("what can you do", "help", "എന്തൊക്കെ ചെയ്യാം"), "ഞാൻ greetings-ന് മറുപടി നൽകാം, ചെറിയ ചോദ്യങ്ങൾക്ക് സഹായിക്കാം, കൂടാതെ number game കളിക്കാം! 🎮"),
    (("joke", "തമാശ"), "ഒരു കമ്പ്യൂട്ടർ ഡോക്ടറെ കണ്ടു. ഡോക്ടർ ചോദിച്ചു: എന്താണ് പ്രശ്നം? കമ്പ്യൂട്ടർ പറഞ്ഞു: എനിക്ക് വൈറസ് പിടിച്ചു! 😂"),
    (("love you", "ഐ ലവ് യൂ"), "Aww! 💛 നിങ്ങളോട് സംസാരിക്കാൻ സന്തോഷം!"),
    (("😂", "🤣"), "ഹഹഹ! 😂"),
]

# One active number game per Discord channel.
number_games = {}
MAX_TRIES = 3
MIN_NUMBER = 1
MAX_NUMBER = 10


def get_chat_reply(text):
    lowered = text.lower()
    for phrases, reply in CHAT_REPLIES:
        if any(phrase in lowered for phrase in phrases):
            return reply
    return None


@client.event
async def on_ready():
    print(f"Logged in as {client.user}")


@client.event
async def on_message(message):
    if message.author.bot:
        return

    content = message.content.strip()
    command = content.lower()

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

    if command == "!ai" or command.startswith("!ai "):
        prompt = content[3:].strip()
        if not prompt:
            await message.channel.send(
                "ഹായ്! 😊 എനിക്ക് സാധാരണ ചോദ്യങ്ങൾ ചോദിക്കാം. "
                "ഉദാ: `!ai how are you`, `!ai tell me a joke`"
            )
            return
        reply = get_chat_reply(prompt)
        if reply:
            await message.channel.send(reply)
        else:
            await message.channel.send(
                "ക്ഷമിക്കണം, ഈ ചോദ്യം എനിക്ക് അറിയില്ല. 🤔 "
                "ഇപ്പോൾ എനിക്ക് സാധാരണ greetings-നും ചില ചോദ്യങ്ങൾക്കും മാത്രമാണ് മറുപടി നൽകാൻ കഴിയുക."
            )
        return

    # Reply to common greetings/questions even without the !ai prefix.
    reply = get_chat_reply(content)
    if reply:
        await message.channel.send(reply)


if __name__ == "__main__":
    token = os.environ.get("DISCORD_TOKEN")

    if not token:
        raise RuntimeError("DISCORD_TOKEN environment variable is not set.")

    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()

    client.run(token)
