import os
import json
import time
import asyncio
from threading import Thread
from flask import Flask
import discord
from discord import app_commands
from dotenv import load_dotenv

# ====== Config ======
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", "0"))
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "1434510458315997325"))
BOT_ROLES_ROLE_ID = int(os.getenv("BOT_ROLES_ROLE_ID", "1401997139675975792"))

STATUS_FILE = "status.json"
PING_TIMEOUT = 120  # secondes max avant de considérer le bot DOWN

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

# ====== Utils ======
last_ping_time = 0

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
    """Envoie un message uniquement en cas de changement de statut."""
    channel = client.get_channel(CHANNEL_ID)
    if not channel:
        print("Salon introuvable.")
        return

    bot_roles_mention = f"<@&{BOT_ROLES_ROLE_ID}>"
    now = discord.utils.format_dt(discord.utils.utcnow(), style='f')

    if is_down:
        msg = f"{bot_roles_mention} est **DOWN** ⛔\n> Détecté le {now}."
    else:
        msg = f"{bot_roles_mention} est de nouveau **UP** ✅\n> Détecté le {now}."

    await channel.send(msg)

# ====== Endpoint ping cronjob ======
@app.route("/")
def cronjob_ping():
    global last_ping_time
    last_ping_time = time.time()
    return "Ping reçu du cronjob."

# ====== Surveillance UP/DOWN ======
async def monitor_bot_status():
    global last_ping_time
    while True:
        previous = read_last_status()
        is_up = (time.time() - last_ping_time) <= PING_TIMEOUT

        # Premier lancement → on enregistre simplement l’état
        if previous is None:
            write_last_status("up" if is_up else "down")
            print(f"Statut initial : {'up' if is_up else 'down'}")
        # Changement : UP → DOWN
        elif previous == "up" and not is_up:
            await send_status_message(True)
            write_last_status("down")
            print("🔴 Bot DOWN")
        # Changement : DOWN → UP
        elif previous == "down" and is_up:
            await send_status_message(False)
            write_last_status("up")
            print("🟢 Bot UP")

        await asyncio.sleep(10)  # vérifie toutes les 10 secondes

# ====== Commande slash ======
@client.tree.command(name="watchdog", description="Vérifie l'état du bot cible")
async def watchdog(interaction: discord.Interaction):
    is_up = (time.time() - last_ping_time) <= PING_TIMEOUT
    status_text = "ONLINE" if is_up else "OFFLINE"
    bot_roles_mention = f"<@&{BOT_ROLES_ROLE_ID}>"

    await interaction.response.send_message(
        f"🤖 Watch Dog est actif !\n"
        f"Le bot {bot_roles_mention} est actuellement **{status_text}**.\n"
        "⚡ Je vous informe automatiquement de son statut.\n"
        "📌 Tous mes messages d'état apparaissent uniquement dans le salon prévu à cet effet."
    )

# ====== Flask thread ======
def run_flask():
    port = int(os.getenv("PORT", 3000))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

# ====== Event on_ready ======
@client.event
async def on_ready():
    print(f"🤖 Connecté en tant que {client.user}")
    Thread(target=run_flask, daemon=True).start()
    asyncio.create_task(monitor_bot_status())
    await client.tree.sync()
    print("✅ Commandes slash synchronisées.")

# ====== Lancement ======
if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("ERREUR : DISCORD_TOKEN manquant dans .env")
    else:
        client.run(DISCORD_TOKEN)
