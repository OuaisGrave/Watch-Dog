import os
import json
import asyncio
from flask import Flask
from threading import Thread
import discord
from discord.ext import commands
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# ====== CONFIGURATION via .env ======
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")               # Token du bot surveillant
GUILD_ID = int(os.getenv("GUILD_ID", "0"))               # ID du serveur
TARGET_BOT_ID = int(os.getenv("TARGET_BOT_ID", "0"))     # ID du bot à surveiller
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "1434510458315997325"))
MEMBRE_ROLE_ID = int(os.getenv("MEMBRE_ROLE_ID", "1402041174298198188"))
BOT_ROLES_ROLE_ID = int(os.getenv("BOT_ROLES_ROLE_ID", "1401997139675975792"))

STATUS_FILE = "status.json"

# ====== INTENTS DISCORD ======
intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.presences = True
intents.messages = True

# ====== CLIENT DISCORD + COMMANDS ======
bot = commands.Bot(command_prefix="!", intents=intents)
app = Flask(__name__)

# ====== UTILS ======
def read_last_status():
    try:
        with open(STATUS_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("status")
    except FileNotFoundError:
        return None

def write_last_status(status):
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump({"status": status}, f, ensure_ascii=False)

async def send_status_message(is_down: bool):
    """Envoie un message dans le salon configuré."""
    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        print("Salon introuvable.")
        return

    membre_mention = f"<@&{MEMBRE_ROLE_ID}>"
    bot_roles_mention = f"<@&{BOT_ROLES_ROLE_ID}>"
    now = discord.utils.format_dt(discord.utils.utcnow(), style='f')

    if is_down:
        msg = f"{membre_mention} • {bot_roles_mention} est **DOWN** ⛔\n> Détecté le {now}."
    else:
        msg = f"{membre_mention} • {bot_roles_mention} est de nouveau **UP** ✅\n> Détecté le {now}."

    await channel.send(msg)

async def check_target_status():
    """Vérifie si le bot cible est online / offline."""
    guild = bot.get_guild(GUILD_ID)
    if not guild:
        print("Serveur introuvable.")
        return

    try:
        member = await guild.fetch_member(TARGET_BOT_ID)
    except discord.NotFound:
        member = None
    except Exception as e:
        print("Erreur fetching member:", e)
        member = None

    presence_status = getattr(member, "status", discord.Status.offline)
    is_up = presence_status != discord.Status.offline
    previous = read_last_status()

    # Si premier run → enregistrer seulement
    if previous is None:
        write_last_status("up" if is_up else "down")
        print(f"Statut initial : {'up' if is_up else 'down'}")
        return

    # Transition DOWN
    if previous == "up" and not is_up:
        await send_status_message(True)
        write_last_status("down")
        print("🔴 Bot est DOWN")

    # Transition UP
    elif previous == "down" and is_up:
        await send_status_message(False)
        write_last_status("up")
        print("🟢 Bot est UP")

    else:
        print("Aucun changement.")

# ====== COMMANDE WATCHDOG ======
@bot.command(name="watchdog")
async def watchdog_status(ctx):
    """Commande pour vérifier que Watch Dog fonctionne et expliquer son rôle."""
    guild = ctx.guild
    target_bot = await guild.fetch_member(TARGET_BOT_ID)
    status = "ONLINE" if target_bot and target_bot.status != discord.Status.offline else "OFFLINE"

    embed = discord.Embed(
        title=f"🤖 Watch Dog est actif !",
        description=(
            f"Le bot cible est actuellement **{status}**.\n\n"
            "Je surveille ce bot et vous avertis automatiquement si son état change.\n"
            "Tous mes messages d’alerte apparaissent uniquement dans ce salon."
        ),
        color=discord.Color.green() if status=="ONLINE" else discord.Color.red()
    )
    await ctx.send(embed=embed)

# ====== FLASK (Render ping) ======
@app.route("/")
def index():
    return "✅ Bot Monitor Actif"

@app.route("/ping")
def ping():
    if not bot.is_ready():
        return "Bot non prêt, vérification non lancée.", 503
    asyncio.run_coroutine_threadsafe(check_target_status(), bot.loop)
    return "Vérification lancée."

def run_flask():
    port = int(os.getenv("PORT", 3000))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

# ====== EVENT ON_READY ======
@bot.event
async def on_ready():
    print(f"🤖 Connecté en tant que {bot.user}")
    Thread(target=run_flask, daemon=True).start()
    # Premier check automatique au démarrage
    asyncio.create_task(check_target_status())

# ====== LANCEMENT ======
if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("ERREUR : DISCORD_TOKEN manquant. Remplis le fichier .env avec DISCORD_TOKEN.")
    else:
        bot.run(DISCORD_TOKEN)
