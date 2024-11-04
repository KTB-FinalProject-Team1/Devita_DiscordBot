import discord
import requests
import os
from dotenv import load_dotenv

load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
JENKINS_URL = os.getenv('JENKINS_URL')
JENKINS_USER = os.getenv('JENKINS_USER')
JENKINS_TOKEN = os.getenv('JENKINS_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
client = discord.client(intents=intents)

@client.event
async def on_ready():
    print(f"Logged in as {client.user}")

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    if message.content.startswith('!test'):
        response = requests.post(
            JENKINS_URL,
            auth=(JENKINS_USER,JENKINS_TOKEN)
        )
        if response.status_code == 201:
            await message.channel.send("Test 파이프라인 배포 성공")
        else:
            await message.channel.send(f"{response.status_code}에러가 발생하였습니다")
client.run(DISCORD_TOKEN)
