# Import the required libraries
import discord
import os
from discord.ext import commands
from dotenv import load_dotenv
import google.generativeai as genai
import asyncio
from telethon import TelegramClient, events
import json
import re
import logging
import time
import sys


# Configura o log de erros
logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("errors.log"),
        logging.StreamHandler()
    ]
)

# Tempo do último evento
last_message_time = time.time()

# Limite de inatividade (em segundos)
TIMEOUT = 300  # 5 minutos

# Função para carregar os canais ativados
def carregar_canais_ativados():
    try:
        with open("canais_ativados.json", "r") as f:
            return set(json.load(f))
    except FileNotFoundError:
        return set()

# Função para salvar os canais ativados
def salvar_canais_ativados():
    with open("canais_ativados.json", "w") as f:
        json.dump(list(canais_ativados), f)

# Função para carregar os interesses dos usuários
def carregar_interesses():
    try:
        with open("interesses.json", "r") as f:
            data = json.load(f)
            return {
                server_id: {
                    user_id: set(interesses)
                    for user_id, interesses in users.items()
                }
                for server_id, users in data.items()
            }
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

# Função para salvar os interesses
def salvar_interesses():
    with open("interesses.json", "w") as f:
        json.dump(
            {
                server_id: {
                    user_id: list(interesses)
                    for user_id, interesses in users.items()
                }
                for server_id, users in interesses_usuarios.items()
            },
            f,
            indent=4,
        )

# Carregar interesses na inicialização
interesses_usuarios = carregar_interesses()

# ---------------------- Canais do Telegram ----------------------
TELEGRAM_CANAIS_ARQUIVO = "canais_telegram.json"

def carregar_canais_telegram():
    try:
        with open(TELEGRAM_CANAIS_ARQUIVO, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def salvar_canais_telegram(canais):
    with open(TELEGRAM_CANAIS_ARQUIVO, "w") as f:
        json.dump(canais, f, indent=4)

# Carregar canais no início
TELEGRAM_CHANNELS = carregar_canais_telegram()



# Telegram Config

API_ID = 20816109
API_HASH = "0fbda742fa2955368f9f8f84c77b4c35"

# Criar o cliente do Telegram
telegram_client = TelegramClient('sessao', API_ID, API_HASH)

# Criar um dicionário para armazenar os canais ativados no Discord
canais_ativados = carregar_canais_ativados()

# Configuração do bot do Discord
intents = discord.Intents.all()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

API_KEY = "AIzaSyCqJ71e1XBN35MZJH4U3iohJ6IQv6OuddQ"  # Substitua pela sua API Key real
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# Dicionário para armazenar o histórico de mensagens por canal
chat_histories = {}

# ------------- Comandos para gerenciar canais monitorados no Telegram -------------

# Caminho do arquivo com os canais salvos
CANAIS_TELEGRAM_PATH = "canais_telegram.json"

# Verifica se o canal está autorizado a modificar os canais monitorados
def autorizado(user_id):
    return str(user_id) == "1034605908463976458"


@bot.command()
async def adicionarcanal(ctx, nome_canal: str):
    if not autorizado(ctx.author.id):
        await ctx.send("❌ Você não tem permissão para usar este comando.")
        return

    nome_canal = nome_canal.lstrip("@")  # Remove @ se for usado
    if nome_canal in TELEGRAM_CHANNELS:
        await ctx.send(f"⚠️ O canal @{nome_canal} já está na lista.")
        return

    TELEGRAM_CHANNELS.append(nome_canal)

    with open(CANAIS_TELEGRAM_PATH, "w") as f:
        json.dump(TELEGRAM_CHANNELS, f, indent=4)

    await ctx.send(f"✅ Canal @{nome_canal} adicionado com sucesso.")


@bot.command()
async def removercanal(ctx, nome_canal: str):
    if not autorizado(ctx.author.id):
        await ctx.send("❌ Você não tem permissão para usar este comando.")
        return

    nome_canal = nome_canal.lstrip("@")
    if nome_canal not in TELEGRAM_CHANNELS:
        await ctx.send(f"⚠️ O canal @{nome_canal} não está na lista.")
        return

    TELEGRAM_CHANNELS.remove(nome_canal)

    with open(CANAIS_TELEGRAM_PATH, "w") as f:
        json.dump(TELEGRAM_CHANNELS, f, indent=4)

    await ctx.send(f"🗑️ Canal @{nome_canal} removido com sucesso.")


@bot.command()
async def canaismonitorados(ctx):
    if not autorizado(ctx.author.id):
        await ctx.send("❌ Você não tem permissão para usar este comando.")
        return

    if not TELEGRAM_CHANNELS:
        await ctx.send("📭 Nenhum canal de Telegram está sendo monitorado no momento.")
        return

    canais_formatados = "\n".join(f"📡 @{canal}" for canal in TELEGRAM_CHANNELS)
    embed = discord.Embed(
        title="📡 Canais de Telegram Monitorados",
        description=canais_formatados,
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed)

# ---------------------- Comando para ativar interesses ----------------------
@bot.command()
async def interesse(ctx, *, item: str):
    """Registra um interesse no servidor atual."""
    server_id = str(ctx.guild.id)
    user_id = str(ctx.author.id)

    if server_id not in interesses_usuarios:
        interesses_usuarios[server_id] = {}

    if user_id not in interesses_usuarios[server_id]:
        interesses_usuarios[server_id][user_id] = set()

    interesses_usuarios[server_id][user_id].add(item.lower())
    salvar_interesses()

    await ctx.send(f"✅ Interesse registrado: **{item}** para {ctx.author.mention}.")


@bot.command()
async def removerinteresse(ctx, *, item: str):
    """Remove um interesse do usuário no servidor atual."""
    server_id = str(ctx.guild.id)
    user_id = str(ctx.author.id)

    if server_id in interesses_usuarios and user_id in interesses_usuarios[server_id]:
        if item.lower() in interesses_usuarios[server_id][user_id]:
            interesses_usuarios[server_id][user_id].remove(item.lower())
            salvar_interesses()
            await ctx.send(f"❌ Interesse removido: **{item}** para {ctx.author.mention}.")
        else:
            await ctx.send(f"⚠ Você não tem **{item}** como interesse.")
    else:
        await ctx.send(f"⚠ Você não tem nenhum interesse registrado neste servidor.")


@bot.command()
async def meusinteresses(ctx):
    """Lista os interesses do usuário no servidor atual."""
    server_id = str(ctx.guild.id)
    user_id = str(ctx.author.id)

    if server_id in interesses_usuarios and user_id in interesses_usuarios[server_id]:
        interesses = "\n".join(f"- {interesse}" for interesse in interesses_usuarios[server_id][user_id])

        embed = discord.Embed(
            title="📌 Seus Interesses",
            description=interesses,
            color=discord.Color.red(),
        )

        icon_url = ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url
        embed.set_footer(text=f"Solicitado por {ctx.author.name}", icon_url=icon_url)

        await ctx.send(embed=embed)
    else:
        await ctx.send("⚠ Você ainda não adicionou nenhum interesse neste servidor.")

# ---------------------- Comando para ativar promoções ----------------------

@bot.command()
async def ativarpromocoes(ctx):
    """Ativa ou desativa o envio de promoções para este canal do Discord."""
    channel_id = ctx.channel.id

    if channel_id in canais_ativados:
        canais_ativados.remove(channel_id)
        await ctx.send("🚫 As promoções do Telegram foram **desativadas** neste canal.")
    else:
        canais_ativados.add(channel_id)
        await ctx.send("✅ As promoções do Telegram foram **ativadas** neste canal.")

    # Salvar os canais ativados
    salvar_canais_ativados()

# ---------------------- Evento do Telegram para capturar mensagens ----------------------

@telegram_client.on(events.NewMessage(chats=TELEGRAM_CHANNELS))
async def handler(event):
    global last_message_time
    last_message_time = time.time()
    try:
        """Envia mensagens do Telegram para canais ativados no Discord e menciona usuários com interesses do servidor correto."""
        mensagem = event.message.text

        print(f"📩 Nova mensagem recebida do Telegram ({event.chat.title}): {mensagem}")  # Debug

        if not canais_ativados:
            print("⚠ Nenhum canal ativado no Discord.")
            return

        # Enviar a mensagem do Telegram para todos os canais ativados no Discord
        for channel_id in canais_ativados:
            channel = bot.get_channel(channel_id)
            if not channel:
                print(f"❌ Erro: Canal {channel_id} não encontrado no Discord!")
                continue

            server_id = str(channel.guild.id)

            interessados = {}  # Dicionário para armazenar usuários interessados no servidor

            # Verificar interesses apenas dos usuários do servidor correto
            if server_id in interesses_usuarios:
                for user_id, interesses in interesses_usuarios[server_id].items():
                    for interesse in interesses:
                        if interesse in mensagem.lower():
                            if user_id not in interessados:
                                interessados[user_id] = []
                            interessados[user_id].append(interesse)

            # Criar a mensagem a ser enviada
            msg_envio = f"📢 **Nova promoção de {event.chat.title}:**\n{mensagem}"

            # Adicionar menções de usuários que têm interesse
            if interessados:
                mentions = " ".join([f"<@{user_id}>" for user_id in interessados.keys()])
                interesses_detectados = ", ".join(set([i for lst in interessados.values() for i in lst]))
                msg_envio += f"\n🔔 Usuários interessados em: **{interesses_detectados}** {mentions}"

            await channel.send(msg_envio)
            print(f"✅ Mensagem enviada para o canal {channel_id} no Discord!")

    except Exception as e:
        logging.error("Erro ao processar mensagem", exc_info=True)

# Watchdog
async def watchdog():
    global last_message_time
    while True:
        await asyncio.sleep(60)
        if time.time() - last_message_time > TIMEOUT:
            logging.error("Watchdog: inatividade detectada no Telegram, reiniciando o bot.")
            os.execv(sys.executable, ['python'] + sys.argv)

# ---------------------- Comandos gerais do discord ----------------------

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    activity = discord.Activity(type=discord.ActivityType.listening, name="Thick Of It - KSI")
    await bot.change_presence(status=discord.Status.do_not_disturb)
    await bot.change_presence(activity=activity)



async def gerar_resposta_com_historico(historico):
    """Gera uma resposta do Gemini com base no histórico de mensagens."""
    response = model.generate_content(historico)
    resposta = response.text
    return resposta


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if bot.user in message.mentions:
        channel_id = message.channel.id
        pergunta = message.content.replace(f"<@{bot.user.id}>", "").strip()

        # Inicializa o histórico para este canal se não existir
        if channel_id not in chat_histories:
            chat_histories[channel_id] = []

        # Adiciona a mensagem do usuário ao histórico
        chat_histories[channel_id].append({"role": "user", "parts": [pergunta]})

        # Obtém a resposta do Gemini com o histórico
        resposta = await gerar_resposta_com_historico(chat_histories[channel_id])

        # Adiciona a resposta do modelo ao histórico
        chat_histories[channel_id].append({"role": "model", "parts": [resposta]})

        await message.channel.send(resposta)

    await bot.process_commands(message)


@bot.command()
async def kickvc(ctx, member: discord.Member, time_str: str):
    """Remove um usuário do canal de voz após um tempo especificado (ex: 3h, 30m, 45s)."""

    # Expressão regular para capturar número + unidade (h, m, s)
    match = re.match(r"(\d+)([hms]?)", time_str.lower())

    if not match:
        await ctx.send("Formato inválido! Use algo como `3h`, `30m` ou `45s`.")
        return

    time_value = int(match.group(1))
    time_unit = match.group(2) or "m"  # Padrão para minutos se a unidade não for especificada

    # Converter para segundos
    if time_unit == "h":
        time_in_seconds = time_value * 3600
    elif time_unit == "m":
        time_in_seconds = time_value * 60
    else:
        time_in_seconds = time_value

    if member.voice and member.voice.channel:
        canal = member.voice.channel
        if not time_str.endswith(("s", "h", "m")):
            await ctx.send(f"{member.mention} será removido da call **{canal.name}** em {time_str}m.")
        else:
            await ctx.send(f"{member.mention} será removido da call **{canal.name}** em {time_str}.")

        await asyncio.sleep(time_in_seconds)

        if member.voice and member.voice.channel:
            await member.move_to(None)
            await ctx.send(f"{member.mention} foi removido da call **{canal.name}**.")
        else:
            await ctx.send(f"{member.mention} já saiu da call antes do tempo acabar.")
    else:
        await ctx.send(f"{member.mention} não está em um canal de voz.")


@kickvc.error
async def kickvc_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Você não tem permissão para desconectar membros.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ Uso correto: `!kickvc @Usuário <tempo_em_minutos>`")


@bot.command()
async def limpar_historico(ctx):
    """Limpa o histórico de mensagens do canal atual."""
    channel_id = ctx.channel.id
    if channel_id in chat_histories:
        del chat_histories[channel_id]
        await ctx.send("Histórico de mensagens limpo.")
    else:
        await ctx.send("Não há histórico para limpar neste canal.")


# Carregar variáveis do .env
load_dotenv()

# Testar se o token foi carregado
token = os.getenv("discord_token")

if token is None:
    print("Erro: Variável discord_token não foi carregada!")
    exit(1)
else:
    print("Token carregado com sucesso!")

# Iniciar o bot do Discord e o TelegramClient
async def start_bot():
    await bot.start(token)

async def start_telegram():
    print("🔄 Iniciando conexão com o Telegram...")
    await telegram_client.start()
    print("✅ Telegram conectado!")
    asyncio.create_task(watchdog())
    await telegram_client.run_until_disconnected()

# Rodando ambos os clientes simultaneamente
# Por este:
async def main():
    await telegram_client.start()
    asyncio.create_task(watchdog())
    print("✅ Telegram conectado!")
    await asyncio.gather(
        telegram_client.run_until_disconnected(),
        bot.start(token)
    )


# Rodando o script
asyncio.run(main())
