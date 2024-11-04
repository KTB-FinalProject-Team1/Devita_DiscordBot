import discord
import requests
import os
from dotenv import load_dotenv

load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
JENKINS_CDURL = os.getenv('JENKINS_CDURL')
JENKINS_OVERURL = os.getenv('JENKINS_OVERURL')
JENKINS_USER = os.getenv('JENKINS_USER')
JENKINS_TOKEN = os.getenv('JENKINS_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"Logged in as {client.user}")

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    if message.channel.id != 1302880514608468070:
        return
    send_channel = client.get_channel(1302880514608468070)
    if message.content.startswith('!over'):
        response = requests.post(
            JENKINS_OVERURL,
            auth=(JENKINS_USER,JENKINS_TOKEN)
        )
        if response.status_code == 201:
            await send_channel.send('테스트 서버들 중지 완료')
        else:
            await send_channel.send(f"{response.status_code}애러가 발생했습니다")
    if message.content.startswith('!test'):
        response = requests.post(
            JENKINS_CDURL,
            auth=(JENKINS_USER,JENKINS_TOKEN)
        )
        if response.status_code == 201:
            await send_channel.send("Test 파이프라인 배포 성공")
        else:
            await send_channel.send(f"{response.status_code}에러가 발생하였습니다")
client.run(DISCORD_TOKEN)
