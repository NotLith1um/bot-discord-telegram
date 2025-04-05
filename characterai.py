import discord
import os
from discord.ext import commands
from dotenv import load_dotenv
from PyCAI2 import client


intents = discord.Intents.all()
intents.message_content = True
client = discord.Client(intents=intents)
bot = commands.Bot(command_prefix='!', intents=intents)

API_KEY = "AIzaSyCqJ71e1XBN35MZJH4U3iohJ6IQv6OuddQ"
client = Client


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    activity = discord.Activity(type=discord.ActivityType.listening, name="Thick Of It - KSI")
    await bot.change_presence(activity=activity)


@bot.event
async def gerar_resposta(pergunta):
    response = model.generate_content(pergunta)
    resposta = response.text
    return resposta

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.author == "315637445234262018>":
        return

    if bot.user in message.mentions:
        pergunta = message.content.replace(f"<@{bot.user.id}>", "").strip()
        resposta = await gerar_resposta(pergunta)
        await message.channel.send(resposta)

    await bot.process_commands(message)

load_dotenv()
bot.run(os.getenv("discord_token"))