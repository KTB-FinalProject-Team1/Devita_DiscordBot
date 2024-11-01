import discord
import requests
import os
from dotenv import load_dotenv

load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
JENKINS_URL = os.getenv('JENKINS_URL')

intents = discord.Intents.default()
