import discord
import requests
import os
import asyncio  # asyncio 모듈 추가
from dotenv import load_dotenv

load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
JENKINS_CDURL = os.getenv('JENKINS_CDURL')  # 파이프라인 트리거 URL
JENKINS_OVERURL = os.getenv('JENKINS_OVERURL')  # 파이프라인 트리거 URL
JENKINS_USER = os.getenv('JENKINS_USER')
JENKINS_TOKEN = os.getenv('JENKINS_TOKEN')
JENKINS_CDCHECKURL = os.getenv('JENKINS_CDCHECKURL')
JNEKINS_OVERCHECKURL = os.getenv('JENKIS_OVERCHECKURL')


intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

async def check_pipeline_status(url, channel, pipeline_name):
    response = requests.get(
            url,
            auth=(JENKINS_USER, JENKINS_TOKEN)
        )
    if response.status_code == 200:
        data = response.json()
        result = data.get('result')
        while True:
                print(f"DEBUG: 파이프라인 상태 확인 - {data}")  # 디버깅용 출력
                if result == 'SUCCESS':
                    await channel.send(f"{pipeline_name} 파이프라인 배포 성공")
                    break
                elif result == 'FAILURE':
                    await channel.send(f"{pipeline_name} 파이프라인 배포 실패")
                    break
                elif result == 'ABORTED':
                    await channel.send(f"{pipeline_name} 파이프라인이 중단되었습니다")
                    break
                else:
                    # 아직 빌드가 진행 중인 경우
                    await asyncio.sleep(15)
    else:
        await channel.send("파이프라인 상태를 가져오지 못했습니다")

@client.event
async def on_ready():
    print(f"Logged in as {client.user}")

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    if message.channel.id != 1302880514608468070:
        return
    if message.content.startswith('!over'):
        await message.channel.send("OVER 파이프라인 실행 중...")
        response = requests.post(
            JENKINS_OVERURL,
            auth=(JENKINS_USER, JENKINS_TOKEN)
        )
        if response.status_code == 201:
            await message.channel.send("OVER 파이프라인이 실행되었습니다. 상태를 확인 중입니다...")
            # 상태 확인 함수 호출
            asyncio.create_task(check_pipeline_status(JENKIS_OVERCHECKURL, message.channel, "OVER"))
        else:
            await message.channel.send(f"{response.status_code} 에러가 발생하였습니다")
    elif message.content.startswith('!test'):
        await message.channel.send("CD 파이프라인 실행 중...")
        response = requests.post(
            JENKINS_CDURL,
            auth=(JENKINS_USER, JENKINS_TOKEN)
        )
        if response.status_code == 201:
            await message.channel.send("CD 파이프라인이 실행되었습니다. 상태를 확인 중입니다...")
            # 상태 확인 함수 호출
            asyncio.create_task(check_pipeline_status(JENKINS_CDCHECKURL, message.channel, "CD"))
        else:
            await message.channel.send(f"{response.status_code} 에러가 발생하였습니다")

client.run(DISCORD_TOKEN)
