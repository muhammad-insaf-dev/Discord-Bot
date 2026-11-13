import os
import random
import threading

from flask import Flask
import discord
from discord import app_commands

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
tree = app_commands.CommandTree(client)

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
    try:
        synced = await tree.sync()
        print(f"Logged in as {client.user}; synced {len(synced)} slash commands.")
    except Exception as error:
        print(f"Slash command sync failed: {error}")


@client.event
async def on_message(message):
    if message.author.bot:
        return
    reply = get_chat_reply(message.content.strip())
    if reply:
        await message.channel.send(reply)


@tree.command(name="ai", description="Ask the bot a common question")
@app_commands.describe(question="Type your question or greeting")
async def ai(interaction: discord.Interaction, question: str):
    reply = get_chat_reply(question)
    if reply:
        await interaction.response.send_message(reply)
    else:
        await interaction.response.send_message(
            "ക്ഷമിക്കണം, ഈ ചോദ്യം എനിക്ക് അറിയില്ല. 🤔 "
            "ഇപ്പോൾ സാധാരണ greetings-നും ചില ചോദ്യങ്ങൾക്കും മാത്രമാണ് മറുപടി നൽകാൻ കഴിയുക."
        )


@tree.command(name="predict", description="Start the number guessing game")
async def predict(interaction: discord.Interaction):
    channel_id = interaction.channel_id
    if channel_id in number_games:
        await interaction.response.send_message(
            "A number game is already running here! Use /guess to guess."
        )
        return

    number_games[channel_id] = {
        "number": random.randint(MIN_NUMBER, MAX_NUMBER),
        "tries": 0,
        "player_id": interaction.user.id,
    }
    await interaction.response.send_message(
        f"🎯 **Number Prediction Game!**\n"
        f"I picked a number from **{MIN_NUMBER} to {MAX_NUMBER}**.\n"
        f"You have **{MAX_TRIES} tries**. Use **/guess** and enter a number!"
    )


@tree.command(name="guess", description="Guess the number in the active game")
@app_commands.describe(number="Choose a number from 1 to 10")
async def guess(interaction: discord.Interaction, number: app_commands.Range[int, 1, 10]):
    game = number_games.get(interaction.channel_id)
    if game is None:
        await interaction.response.send_message("Start a game first with /predict.")
        return
    if interaction.user.id != game["player_id"]:
        await interaction.response.send_message(
            "This game belongs to the player who started it.", ephemeral=True
        )
        return

    game["tries"] += 1
    answer = game["number"]
    if number == answer:
        del number_games[interaction.channel_id]
        await interaction.response.send_message(
            f"🎉 **Correct!** The number was **{answer}**. "
            f"You won in **{game['tries']}** attempt(s)!"
        )
    elif game["tries"] >= MAX_TRIES:
        del number_games[interaction.channel_id]
        await interaction.response.send_message(
            f"❌ Game over! The number was **{answer}**. Start again with /predict."
        )
    elif number < answer:
        await interaction.response.send_message(
            f"⬆️ Too low! Try a higher number. **{MAX_TRIES - game['tries']} tries left.**"
        )
    else:
        await interaction.response.send_message(
            f"⬇️ Too high! Try a lower number. **{MAX_TRIES - game['tries']} tries left.**"
        )


@tree.command(name="stopguess", description="Stop your active number guessing game")
async def stopguess(interaction: discord.Interaction):
    game = number_games.get(interaction.channel_id)
    if game is None:
        await interaction.response.send_message("There is no active number game here.")
    elif interaction.user.id != game["player_id"]:
        await interaction.response.send_message(
            "Only the player who started the game can stop it.", ephemeral=True
        )
    else:
        del number_games[interaction.channel_id]
        await interaction.response.send_message("🛑 Number game stopped.")


if __name__ == "__main__":
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_TOKEN environment variable is not set.")

    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()
    client.run(token)
