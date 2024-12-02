import discord
from discord.ext import commands
import requests
import os
import time
import asyncio
from dotenv import load_dotenv

load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
JENKINS_CDURL = os.getenv('JENKINS_CDURL')  # CD 파이프라인 URL
JENKINS_OVERURL = os.getenv('JENKINS_OVERURL')  # OVER 파이프라인 URL
JENKINS_AIURL = os.getenv('JENKINS_AIURL')
JENKINS_BACKURL = os.getenv('JENKINS_BACKURL')
JENKINS_FRONTURL = os.getenv('JENKINS_FRONTURL')

JENKINS_DEPLOYURL = os.getenv('JENKINS_DEPLOYURL')
JENKINS_DEPLOYOVERURL = os.getenv('JENKINS_DEPLOYOVERURL')
JENKINS_AIDEPLOYURL = os.getenv('JENKINS_AIDEPLOYURL')
JENKINS_BACKDEPLOYURL = os.getenv('JENKINS_BACKDEPLOYURL')

JENKINS_USER = os.getenv('JENKINS_USER')
JENKINS_TOKEN = os.getenv('JENKINS_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

def get_current_build_number(jobName):
    for i in range(10):  # 최대 10번 재시도
        url = f"http://localhost:8080/job/{jobName}/lastBuild/api/json"
        response = requests.get(url, auth=(JENKINS_USER, JENKINS_TOKEN))
        if response.status_code == 200:
            data = response.json()
            print(f"DEBUG: 파이프라인 내용 - {data}")
            if data.get('building', False):
                return data['number']
        print(f"DEBUG: 번호 가져오기 시도 {i + 1} 번")
        time.sleep(15)
    return None

async def check_pipeline_status(channel, pipeline_name):
    builNum = get_current_build_number(pipeline_name)
    print(f"DEBUG: 현재 빌드 번호 - {builNum}")
    if not builNum:
        await channel.send(f"{pipeline_name} 실행 중인 빌드 번호를 가져오지 못했습니다.")
        return
    realURL = f"http://localhost:8080/job/{pipeline_name}/{builNum}/api/json"
    print(f"DEBUG: 요청 URL - {realURL}")
    while True:
        response = requests.get(
            realURL,
            auth=(JENKINS_USER, JENKINS_TOKEN)
        )
        print(f"DEBUG: 응답 코드 - {response}")
        if response.status_code == 200:
            data = response.json()
            result = data.get('result')
            print(f"DEBUG: 파이프라인 상태 확인 - {data}")
            if result == 'SUCCESS':
                await channel.send(f"{pipeline_name} 파이프라인 성공")
                break
            elif result == 'FAILURE':
                await channel.send(f"{pipeline_name} 파이프라인 실패")
                break
            elif result == 'ABORTED':
                await channel.send(f"{pipeline_name} 파이프라인이 중단되었습니다")
                break
            else:
                await asyncio.sleep(15)  # 진행 중인 경우 15초 대기
        else:
            await channel.send(f"파이프라인 상태를 가져오지 못했습니다. URL: {realURL}")
            break

class PipelineView(discord.ui.View):
    @discord.ui.button(label="테스트 배포", style=discord.ButtonStyle.green)
    async def cd_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("CD 파이프라인 실행 중...")
        response = requests.post(
            JENKINS_CDURL,
            auth=(JENKINS_USER, JENKINS_TOKEN)
        )
        if response.status_code == 201:
            await interaction.channel.send("CD 파이프라인이 실행되었습니다. 상태를 확인 중입니다...")
            asyncio.create_task(check_pipeline_status(interaction.channel, "cd_pipeline"))
        else:
            await interaction.channel.send(f"CD 파이프라인 실행 실패. 에러 코드: {response.status_code}")

    @discord.ui.button(label="테스트 종료", style=discord.ButtonStyle.green)
    async def over_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("OVER 파이프라인 실행 중...")
        response = requests.post(
            JENKINS_OVERURL,
            auth=(JENKINS_USER, JENKINS_TOKEN)
        )
        if response.status_code == 201:
            await interaction.channel.send("OVER 파이프라인이 실행되었습니다. 상태를 확인 중입니다...")
            asyncio.create_task(check_pipeline_status(interaction.channel, "testOver_pipeline"))
        else:
            await interaction.channel.send(f"OVER 파이프라인 실행 실패. 에러 코드: {response.status_code}")

    @discord.ui.button(label="Ai Test 재빌드", style=discord.ButtonStyle.green)
    async def ai_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("AI 파이프라인 실행 중...")
        response = requests.post(
            JENKINS_AIURL,
            auth=(JENKINS_USER, JENKINS_TOKEN)
        )
        if response.status_code == 201:
            await interaction.channel.send("AI 파이프라인이 실행되었습니다. 상태를 확인 중입니다...")
            asyncio.create_task(check_pipeline_status(interaction.channel, "ai_pipeline"))
        else:
            await interaction.channel.send(f"AI 파이프라인 실행 실패. 에러 코드: {response.status_code}")

    @discord.ui.button(label="Back Test 재빌드", style=discord.ButtonStyle.green)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Back 파이프라인 실행 중...")
        response = requests.post(
            JENKINS_BACKURL,
            auth=(JENKINS_USER, JENKINS_TOKEN)
        )
        if response.status_code == 201:
            await interaction.channel.send("Back 파이프라인이 실행되었습니다. 상태를 확인 중입니다...")
            asyncio.create_task(check_pipeline_status(interaction.channel, "back_pipeline"))
        else:
            await interaction.channel.send(f"Back 파이프라인 실행 실패. 에러 코드: {response.status_code}")
    
    @discord.ui.button(label="Front Test 재빌드", style=discord.ButtonStyle.green)
    async def front_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Front 파이프라인 실행 중...")
        response = requests.post(
            JENKINS_AIURL,
            auth=(JENKINS_USER, JENKINS_TOKEN)
        )
        if response.status_code == 201:
            await interaction.channel.send("Front 파이프라인이 실행되었습니다. 상태를 확인 중입니다...")
            asyncio.create_task(check_pipeline_status(interaction.channel, "front_new_pipeline"))
        else:
            await interaction.channel.send(f"Front 파이프라인 실행 실패. 에러 코드: {response.status_code}")
    
    @discord.ui.button(label="배포", style=style=discord.ButtonStyle.danger)
    async def front_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("배포 중...")
        response = requests.post(
            JENKINS_AIURL,
            auth=(JENKINS_USER, JENKINS_TOKEN)
        )
        if response.status_code == 201:
            await interaction.channel.send("Front 파이프라인이 실행되었습니다. 상태를 확인 중입니다...")
            asyncio.create_task(check_pipeline_status(interaction.channel, "front_new_pipeline"))
        else:
            await interaction.channel.send(f"Front 파이프라인 실행 실패. 에러 코드: {response.status_code}")
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.command(name="bot")
async def bot_command(ctx):
    view = PipelineView()
    await ctx.send("어떤 파이프라인을 실행할까요?", view=view)

bot.run(DISCORD_TOKEN)
