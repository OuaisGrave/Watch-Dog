import os
import json
import time
import asyncio
from threading import Thread
from flask import Flask
import discord
from discord import app_commands
from dotenv import load_dotenv

# ====== Configuration ======
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", "0"))
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))
BOT_ROLES_ROLE_ID = int(os.getenv("BOT_ROLES_ROLE_ID", "0"))

STATUS_FILE = "status.json"
PING_FILE = "ping_time.txt"
PING_TIMEOUT = 180  # secondes avant de considérer le bot DOWN
CHECK_INTERVAL = 10  # secondes entre vérifications

# ====== Discord ======
intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.presences = True
intents.messages = True

class WatchDogClient(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

client = WatchDogClient()
app = Flask(__name__)

# ====== Fonctions utilitaires ======
def read_last_status() -> str | None:
    """Lit le dernier statut (up/down) enregistré."""
    try:
        with open(STATUS_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("status")
    except FileNotFoundError:
        return None

def write_last_status(status: str):
    """Écrit le statut actuel (up/down)."""
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump({"status": status}, f, ensure_ascii=False)

def read_last_ping_time() -> float:
    """Lit le dernier timestamp de ping reçu."""
    try:
        with open(PING_FILE, "r") as f:
            return float(f.read().strip())
    except (FileNotFoundError, ValueError):
        return 0.0

def write_last_ping_time():
    """Enregistre l'heure actuelle comme dernier ping reçu."""
    with open(PING_FILE, "w") as f:
        f.write(str(time.time()))

async def send_status_message(is_down: bool):
    """Envoie un message dans le salon uniquement si changement de statut."""
    channel = client.get_channel(CHANNEL_ID)
    if not channel:
        print("⚠️ Salon introuvable ou inaccessible.")
        return

    bot_roles_mention = f"<@&{BOT_ROLES_ROLE_ID}>"
    now = discord.utils.format_dt(discord.utils.utcnow(), style='f')

    if is_down:
        msg = f"{bot_roles_mention} est **DOWN** ⛔\n> Détecté le {now}."
    else:
        msg = f"{bot_roles_mention} est de nouveau **UP** ✅\n> Détecté le {now}."

    await channel.send(msg)

# ====== Endpoint Flask pour le ping ======
@app.route("/")
def receive_ping():
    """Reçoit les pings du cronjob ou du bot surveillé."""
    write_last_ping_time()
    print(f"[{time.strftime('%H:%M:%S')}] ✅ Ping reçu.")
    return "Ping OK"

# ====== Tâche de surveillance ======
async def monitor_bot_status():
    """Boucle asynchrone qui vérifie si le bot est UP ou DOWN."""
    while True:
        last_ping = read_last_ping_time()
        previous = read_last_status()
        is_up = (time.time() - last_ping) <= PING_TIMEOUT

        if previous is None:
            # Premier lancement : on initialise
            write_last_status("up" if is_up else "down")
            print(f"🚀 Statut initial : {'UP' if is_up else 'DOWN'}")

        elif previous == "up" and not is_up:
            await send_status_message(True)
            write_last_status("down")
            print("🔴 Bot DOWN détecté.")

        elif previous == "down" and is_up:
            await send_status_message(False)
            write_last_status("up")
            print("🟢 Bot UP détecté.")

        await asyncio.sleep(CHECK_INTERVAL)

# ====== Commande slash Discord ======
@client.tree.command(name="watchdog", description="Vérifie l'état du bot surveillé")
async def watchdog(interaction: discord.Interaction):
    last_ping = read_last_ping_time()
    is_up = (time.time() - last_ping) <= PING_TIMEOUT
    status_text = "🟢 ONLINE" if is_up else "🔴 OFFLINE"
    bot_roles_mention = f"<@&{BOT_ROLES_ROLE_ID}>"

    await interaction.response.send_message(
        f"🤖 **WatchDog actif !**\n"
        f"Le bot {bot_roles_mention} est actuellement **{status_text}**.\n"
        "⚡ Je signale automatiquement tout changement de statut ici."
    )

# ====== Flask dans un thread séparé ======
def run_flask():
    port = int(os.getenv("PORT", 3000))
    print(f"🌐 Serveur Flask lancé sur le port {port}")
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

# ====== Événements Discord ======
@client.event
async def on_ready():
    print(f"🤖 Connecté en tant que {client.user}")
    Thread(target=run_flask, daemon=True).start()
    await asyncio.sleep(2)  # petite pause pour laisser Flask démarrer
    asyncio.create_task(monitor_bot_status())
    await client.tree.sync()
    print("✅ Commandes slash synchronisées et surveillance démarrée.")

# ====== Lancement ======
if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("❌ ERREUR : DISCORD_TOKEN manquant dans .env")
    else:
        client.run(DISCORD_TOKEN)