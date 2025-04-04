import discord
import random
import asyncio
import string
import json
import time
from flask import Flask
import threading
import os
from dotenv import load_dotenv
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta

app = Flask(__name__)

@app.route('/')
def home():
    return "Ocarina Gen Bot is running!"

def run_web():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 7070)))

load_dotenv()  # Charger les variables d'environnement
TOKEN = os.getenv("DISCORD_TOKEN")

GUILD_ID = 1339280322805764098  # Remplace par l'ID de ton serveur
GEN_ROLE_NAME = "Gen Free"  # Nom du rôle à attribuer
STOCK_ROLE_NAME = "Owner"  # Nom du rôle pour voir le stock
ALLOWED_CHANNEL_ID = 1349784316049362964 # Remplace par l'ID du salon où les commandes sont autorisées
ALLOWED_CHANNEL_AVIS = 1346573719484633171 # ID du salon où les avis seront envoyés
GEN_CHANNEL_ID = 1349784316049362964  # ID du salon +gen où les messages seront supprimés
LOG_CHANNEL_ID = 1355953070760132723

# Fichier JSON pour sauvegarder le stock
STOCK_FILE = "stock.json"

# Liste des bases pour chaque service
SERVICES = {
    "nitro": "https://discord.gift/{random_id_nitro}",
    "vbucks": "https://fortnite.com/vbucks/{random_id_vbucks}",
    "discord": "{email}:{password}"
}

# Charger le stock depuis le fichier JSON
def load_stock():
    try:
        with open(STOCK_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Si le fichier n'existe pas ou est corrompu, on retourne le stock par défaut
        return {
            "nitro": 100,
            "vbucks": 50,
            "discord": 75
        }

# Sauvegarder le stock dans un fichier JSON
def save_stock(stock):
    with open(STOCK_FILE, "w") as f:
        json.dump(stock, f, indent=4)

# Initialiser le stock en chargeant les données
STOCK = load_stock()
last_update_time = datetime.now()

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="+", intents=intents)
tree = bot.tree

@bot.event
async def on_ready():
    print(f"{bot.user} est connecté !")
    await tree.sync(guild=discord.Object(id=GUILD_ID))
    print("Commandes slash synchronisées.")
    bot.loop.create_task(check_status_loop())
    
# 📌 Vérification des statuts et mise à jour des rôles
async def check_status_loop():
    await bot.wait_until_ready()
    guild = bot.get_guild(GUILD_ID)
    if not guild:
        return

    while not bot.is_closed():
        role = discord.utils.get(guild.roles, name=GEN_ROLE_NAME)
        if not role:
            print(f"⚠️ Rôle '{GEN_ROLE_NAME}' non trouvé !")
            await asyncio.sleep(300)
            continue

        bot_member = guild.me
        for member in guild.members:
            if member.bot:
                continue

            has_required_status = any(
                activity and isinstance(activity, discord.CustomActivity) and ".gg/ocarina" in activity.name.lower()
                for activity in member.activities
            )

            if has_required_status and role not in member.roles:
                await member.add_roles(role)
                print(f"✅ Rôle '{GEN_ROLE_NAME}' ajouté à {member.display_name}")
            elif not has_required_status and role in member.roles:
                if bot_member.top_role > role:
                    await member.remove_roles(role)
                    print(f"❌ Rôle '{GEN_ROLE_NAME}' retiré de {member.display_name}")
                else:
                    print(f"⚠️ Impossible de retirer '{GEN_ROLE_NAME}' de {member.display_name} (rôle trop haut)")

        await asyncio.sleep(60)  # Vérifie toutes 60 secondes

# Fonction d'autocomplétion pour les services
async def service_autocomplete(interaction: discord.Interaction, current: str):
    try:
        # Filtrer les services correspondant à la recherche
        choices = [
            app_commands.Choice(name=svc, value=svc)
            for svc in SERVICES
            if current.lower() in svc.lower()
        ]

        # Si aucun choix, retourne une liste vide
        if not choices:
            choices = [app_commands.Choice(name="Aucun service trouvé", value="none")]

        # Envoyer les choix en réponse
        await interaction.response.autocomplete(choices)

    except Exception as e:
        # Log des erreurs pour le diagnostic
        print(f"Erreur dans l'autocomplétion : {e}")

def generate_realistic_email():
    prenoms = ["alex", "julien", "marie", "lucas", "emma", "nathan", "lea", "sophie", "theo"]
    noms = ["durand", "martin", "bernard", "dubois", "morel", "girard", "leclerc", "rousseau"]
    
    prenom = random.choice(prenoms)
    nom = random.choice(noms)
    chiffre = random.randint(10, 99)  # Ajoute un chiffre pour plus de réalisme
    
    return f"{prenom}.{nom}{chiffre}@gmail.com"

def generate_simple_password():
    mots = ["panda", "summer", "gaming", "rocket", "sunshine", "winter", "dragon", "shadow"]
    mot = random.choice(mots)  # Choisit un mot courant
    chiffres = str(random.randint(10, 99))  # Ajoute 2 chiffres
    majuscule = random.choice(string.ascii_uppercase)  # Ajoute une majuscule
    
    return mot + chiffres + majuscule
    
# 📌 Commande `/gen`
@tree.command(name="gen", description="Génère un compte", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(service="Le service que vous voulez générer")
@app_commands.autocomplete(service=service_autocomplete)
async def gen(interaction: discord.Interaction, service: str):
    global last_update_time

    try:
        # Vérifie si la commande est utilisée dans le bon salon
        if interaction.channel.id != ALLOWED_CHANNEL_ID:
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    f"⛔ Cette commande ne peut être utilisée que dans le salon <#{ALLOWED_CHANNEL_ID}>.",
                    ephemeral=True
                )
            return

        # Vérifie si l'utilisateur a le bon rôle
        role = discord.utils.get(interaction.guild.roles, name=GEN_ROLE_NAME)
        if role not in interaction.user.roles:
            if not interaction.response.is_done():
                await interaction.response.send_message("⛔ Tu n'as pas accès à cette commande.", ephemeral=True)
            return

        # Vérifie si le service existe
        if service.lower() not in SERVICES:
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ Service inconnu.", ephemeral=True)
            return

        # Vérifie si le stock est disponible
        if STOCK.get(service.lower(), 0) <= 0:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"❌ Stock épuisé pour `{service}`.", ephemeral=True)
            return

        # Génération d'un compte aléatoire
        account = None
        if service.lower() == "nitro":
            random_id_nitro = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
            account = SERVICES[service.lower()].format(random_id_nitro=random_id_nitro)
        elif service.lower() == "vbucks":
            random_id_vbucks = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
            account = SERVICES[service.lower()].format(random_id_vbucks=random_id_vbucks)
        elif service.lower() == "discord":
            email = generate_realistic_email()
            password = generate_simple_password()
            account = f"{email}:{password}"

        # Mise à jour du stock
        STOCK[service.lower()] -= 1
        save_stock(STOCK)
        last_update_time = datetime.now()

        # Envoie le compte en MP
        try:
            await interaction.user.send(f"Voici ton compte {service} : `{account}`")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "✅ Ton compte a été envoyé en MP ! Merci d'utiliser le bot.",
                    ephemeral=True
                )
        except discord.Forbidden:
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ Impossible d'envoyer un MP. Active tes messages privés.",
                    ephemeral=True
                )
            return

        # Logs : envoyés une seule fois après succès
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            log_embed = discord.Embed(title="📃 Génération de compte", color=0x00ff00)
            log_embed.add_field(name="👤 Utilisateur", value=f"{interaction.user.mention}", inline=True)
            log_embed.add_field(name="📌 Service", value=service, inline=True)
            log_embed.add_field(name="🕒 Heure", value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), inline=False)
            await log_channel.send(embed=log_embed)

    except Exception as e:
        # Gestion des erreurs générales
        print(f"Erreur lors de la commande /gen : {e}")
        if not interaction.response.is_done():
            await interaction.response.send_message(
                "❌ Une erreur inattendue s'est produite. Merci de réessayer plus tard.",
                ephemeral=True
            )

# 📌 Commande `/stock`
@tree.command(name="stock", description="Affiche l'état du stock", guild=discord.Object(id=GUILD_ID))
async def stock(interaction: discord.Interaction):
    try:
        # Calcul de la différence de temps depuis la dernière mise à jour
        time_diff = datetime.now() - last_update_time
        hours, minutes = divmod(time_diff.total_seconds() // 60, 60)
        elapsed_time = f"{int(hours)}h {int(minutes)}m"

        # Création de l'embed pour afficher le stock
        embed = discord.Embed(title="📦 Ocarina Gen Stock", color=0x00ff00)
        for service, count in STOCK.items():
            status = f"`{count} compte(s) restant(s)`" if count > 0 else "🔴 `Service vide`"
            embed.add_field(name=f"📌 {service}", value=status, inline=False)
        embed.set_footer(text=f"🕒 Dernière mise à jour il y a {elapsed_time}")

        # Envoi de la réponse dans le salon d'origine
        await interaction.response.send_message(embed=embed, ephemeral=False)

    except Exception as e:
        # Gestion des erreurs générales
        print(f"Erreur dans la commande /stock : {e}")
        await interaction.response.send_message(
            "❌ Une erreur inattendue s'est produite lors de l'affichage du stock.",
            ephemeral=True
        )

# 📌 Commande `/addstock`
@tree.command(name="addstock", description="Ajoute du stock à un service", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(service="Le service auquel tu veux ajouter du stock", quantity="La quantité à ajouter")
@app_commands.autocomplete(service=service_autocomplete)
async def addstock(interaction: discord.Interaction, service: str, quantity: int):
    try:
        # Vérifier si l'utilisateur a le rôle "Owner"
        role = discord.utils.get(interaction.guild.roles, name=STOCK_ROLE_NAME)
        if role not in interaction.user.roles:
            await interaction.response.send_message(
                "⛔ Tu n'as pas les permissions pour cette commande.",
                ephemeral=True
            )
            return

        # Vérifier si le service existe
        if service.lower() not in SERVICES:
            await interaction.response.send_message(
                "❌ Service inconnu.",
                ephemeral=True
            )
            return

        # Vérifier si la quantité est valide
        if quantity <= 0:
            await interaction.response.send_message(
                "❌ Quantité invalide. Elle doit être supérieure à 0.",
                ephemeral=True
            )
            return

        # Ajouter la quantité au stock
        STOCK[service.lower()] = STOCK.get(service.lower(), 0) + quantity
        save_stock(STOCK)

        # Réponse de confirmation
        await interaction.response.send_message(
            f"✅ {quantity} compte(s) ajouté(s) à `{service}`.",
            ephemeral=True
        )

        # Envoyer un log dans le salon de logs
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            log_embed = discord.Embed(title="📦 Mise à jour du stock", color=0x00ff00)
            log_embed.add_field(name="👤 Action réalisée par", value=f"{interaction.user.mention}", inline=True)
            log_embed.add_field(name="📌 Service", value=service, inline=True)
            log_embed.add_field(name="➕ Quantité ajoutée", value=str(quantity), inline=True)
            log_embed.add_field(name="📆 Heure", value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), inline=False)
            await log_channel.send(embed=log_embed)

    except Exception as e:
        # Gestion des erreurs
        print(f"Erreur lors de l'exécution de la commande /addstock : {e}")
        await interaction.response.send_message(
            "❌ Une erreur inattendue s'est produite.",
            ephemeral=True
        )

# 📌 Commande `/removestock`
@tree.command(name="removestock", description="Retire du stock d'un service", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(service="Le service dont tu veux retirer du stock", quantity="La quantité à retirer")
@app_commands.autocomplete(service=service_autocomplete)
async def removestock(interaction: discord.Interaction, service: str, quantity: int):
    try:
        # Vérifier si l'utilisateur a le rôle "Owner"
        role = discord.utils.get(interaction.guild.roles, name=STOCK_ROLE_NAME)
        if role not in interaction.user.roles:
            await interaction.response.send_message(
                "⛔ Tu n'as pas les permissions pour cette commande.",
                ephemeral=True
            )
            return

        # Vérifier si le service existe
        if service.lower() not in SERVICES:
            await interaction.response.send_message(
                "❌ Service inconnu.",
                ephemeral=True
            )
            return

        # Vérifier si la quantité est valide
        if quantity <= 0 or STOCK.get(service.lower(), 0) < quantity:
            await interaction.response.send_message(
                "❌ Quantité invalide ou insuffisante dans le stock.",
                ephemeral=True
            )
            return

        # Retirer la quantité du stock
        STOCK[service.lower()] -= quantity
        save_stock(STOCK)

        # Réponse de confirmation
        await interaction.response.send_message(
            f"✅ {quantity} compte(s) retiré(s) de `{service}`.",
            ephemeral=True
        )

        # Envoi d'un log (facultatif)
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            log_embed = discord.Embed(title="📦 Mise à jour du stock", color=0x00ff00)
            log_embed.add_field(name="👤 Action réalisée par", value=f"{interaction.user.mention}", inline=True)
            log_embed.add_field(name="📌 Service", value=service, inline=True)
            log_embed.add_field(name="➖ Quantité retirée", value=str(quantity), inline=True)
            log_embed.add_field(name="📆 Heure", value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), inline=False)
            await log_channel.send(embed=log_embed)
    except Exception as e:
        # Gestion des erreurs
        print(f"Erreur lors de l'exécution de la commande /removestock : {e}")
        await interaction.response.send_message(
            "❌ Une erreur inattendue s'est produite.",
            ephemeral=True
        )

# 📌 Commande `/avis`
@tree.command(name="avis", description="Permet de donner un avis sur un service", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(service="Le service sur lequel tu veux donner un avis", avis="Ton avis sur le service")
@app_commands.autocomplete(service=service_autocomplete)
async def avis(interaction: discord.Interaction, service: str, avis: str):
    # Vérifier si le service existe
    if service.lower() not in SERVICES:
        await interaction.response.send_message("❌ Service inconnu.", ephemeral=True)
        return

    if not avis.strip():
        await interaction.response.send_message("❌ L'avis ne peut pas être vide.", ephemeral=True)
        return

    # Créer l'embed pour le message
    embed = discord.Embed(title="📢 Avis sur un service", color=0x00ff00)
    embed.add_field(name="👤 Utilisateur", value=f"{interaction.user.mention}", inline=True)
    embed.add_field(name="📌 Service", value=service, inline=True)
    embed.add_field(name="✍️ Avis", value=avis, inline=False)
    embed.set_footer(text="Merci pour ton avis !")

    # Envoyer l'embed dans le salon configuré
    channel = bot.get_channel(ALLOWED_CHANNEL_AVIS)
    if channel:
        await channel.send(embed=embed)
        await interaction.response.send_message("✅ Ton avis a été envoyé ! Merci 🙌", ephemeral=True)
    else:
        await interaction.response.send_message("❌ Salon de destination introuvable.", ephemeral=True)

port = int(os.environ.get("PORT", 7070))
threading.Thread(target=run_web).start()

bot.run(TOKEN)
