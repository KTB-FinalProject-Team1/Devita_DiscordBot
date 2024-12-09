import discord
from discord.ext import commands
import requests
import os
import time
import asyncio
from dotenv import load_dotenv
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from flask import Flask
from threading import Thread

app = Flask(__name__)

@app.route("/")
def health_check():
    return "OK",200

def run():
    app.run(host="0.0.0.0", port=8000)




Thread(target=run).start()

load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
DISCORD_CHANNEL_ID = int(os.getenv('DISCORD_CHANNEL_ID'))

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

AWS_REGION = os.getenv('AWS_REGION')
JENKINS_INSTANCE_ID = os.getenv('JENKINS_INSTANCE_ID')

ec2 = boto3.client(
    'ec2',
    region_name=AWS_REGION,
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
)


intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@app.route("/jenkins",methods=["POST"])
def jenkins_webhook():
    data = requests.get_json()
    message = data.get("message", "Jenkins에서 전송된 메시지입니다.")
    send_message_to_discord(message)
    return {"status":"Message sent"},200

async def send_discord_message(message):
    channel = bot.get_channel(DISCORD_CHANNEL_ID)
    if channel:
        await channel.send(message)

def send_message_to_discord(message):
    asyncio.run(send_discord_message(message))



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
    @discord.ui.button(label="Jenkins 시작",style=discord.ButtonStyle.blurple)
    async def start_jenkins_button(self,interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Jenkins 실행 중...")
        try:
            response = ec2.start_instances(InstanceIds=[JENKINS_INSTANCE_ID])
            waiter = ec2.get_waiter('instance_running')
            waiter.wait(InstanceIds=[JENKINS_INSTANCE_ID])

            await interaction.channel.send("JENKINS 실행 완료")
        except (BotoCoreError, ClientError) as error:
            await interaction.channel.send(f"Jenkins 인스턴스를 시작하지 못했습니다: {error}")
    
    @discord.ui.button(label="Jenkins 중지", style=discord.ButtonStyle.blurple)
    async def stop_jenkins_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Jenkins 인스턴스를 중지 중입니다...")
        try:
            # EC2 인스턴스 중지
            response = ec2.stop_instances(InstanceIds=[JENKINS_INSTANCE_ID])

            # 인스턴스 상태 확인
            waiter = ec2.get_waiter('instance_stopped')
            waiter.wait(InstanceIds=[JENKINS_INSTANCE_ID])

            await interaction.channel.send("Jenkins 중지 완료")
        except (BotoCoreError, ClientError) as error:
            await interaction.channel.send(f"Jenkins 인스턴스를 중지하지 못했습니다: {error}")

    @discord.ui.button(label="테스트 배포", style=discord.ButtonStyle.green)
    async def cd_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("CD 파이프라인 실행 중...")
        response = requests.post(
            JENKINS_CDURL,
            auth=(JENKINS_USER, JENKINS_TOKEN)
        )
        if response.status_code == 201:
            await interaction.channel.send("CD 파이프라인이 실행되었습니다. 상태를 확인 중입니다...")
            asyncio.create_task(check_pipeline_status(interaction.channel, "cd_pipeline_test"))
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
            asyncio.create_task(check_pipeline_status(interaction.channel, "testOver_pipeline_test"))
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
            asyncio.create_task(check_pipeline_status(interaction.channel, "ai_pipeline_test"))
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
            asyncio.create_task(check_pipeline_status(interaction.channel, "back_pipeline_test"))
        else:
            await interaction.channel.send(f"Back 파이프라인 실행 실패. 에러 코드: {response.status_code}")
    
    @discord.ui.button(label="Front Test 재빌드", style=discord.ButtonStyle.green)
    async def frontTest_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Front 파이프라인 실행 중...")
        response = requests.post(
            JENKINS_FRONTURL,
            auth=(JENKINS_USER, JENKINS_TOKEN)
        )
        if response.status_code == 201:
            await interaction.channel.send("Front 파이프라인이 실행되었습니다. 상태를 확인 중입니다...")
            asyncio.create_task(check_pipeline_status(interaction.channel, "front_pipeline_test"))
        else:
            await interaction.channel.send(f"Front 파이프라인 실행 실패. 에러 코드: {response.status_code}")
    
    @discord.ui.button(label="배포", style=discord.ButtonStyle.danger)
    async def deploy_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("배포 중...")
        response = requests.post(
            JENKINS_DEPLOYURL,
            auth=(JENKINS_USER, JENKINS_TOKEN)
        )
        if response.status_code == 201:
            await interaction.channel.send("배포 파이프라인이 실행되었습니다. 상태를 확인 중입니다...")
            asyncio.create_task(check_pipeline_status(interaction.channel, "cd_pipeline_deploy"))
        else:
            await interaction.channel.send(f"배포 파이프라인 실행 실패. 에러 코드: {response.status_code}")

    @discord.ui.button(label="배포중단", style=discord.ButtonStyle.danger)
    async def deployOver_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("배포 중단 중...")
        response = requests.post(
            JENKINS_DEPLOYOVERURL,
            auth=(JENKINS_USER, JENKINS_TOKEN)
        )
        if response.status_code == 201:
            await interaction.channel.send("배포중단 파이프라인이 실행되었습니다. 상태를 확인 중입니다...")
            asyncio.create_task(check_pipeline_status(interaction.channel, "deployOver_pipeline_deploy"))
        else:
            await interaction.channel.send(f"배포중단 파이프라인 실행 실패. 에러 코드: {response.status_code}")

    @discord.ui.button(label="Back 재배포", style=discord.ButtonStyle.danger)
    async def deployBack_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Back 재배포 중...")
        response = requests.post(
            JENKINS_BACKDEPLOYURL,
            auth=(JENKINS_USER, JENKINS_TOKEN)
        )
        if response.status_code == 201:
            await interaction.channel.send("Back 재배포 파이프라인이 실행되었습니다. 상태를 확인 중입니다...")
            asyncio.create_task(check_pipeline_status(interaction.channel, "back_pipeline_deploy"))
        else:
            await interaction.channel.send(f"Back 재배포 파이프라인 실행 실패. 에러 코드: {response.status_code}")

    @discord.ui.button(label="AI 재배포", style=discord.ButtonStyle.danger)
    async def deployAi_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("AI 재배포 중...")
        response = requests.post(
            JENKINS_AIDEPLOYURL,
            auth=(JENKINS_USER, JENKINS_TOKEN)
        )
        if response.status_code == 201:
            await interaction.channel.send("AI 재배포 파이프라인이 실행되었습니다. 상태를 확인 중입니다...")
            asyncio.create_task(check_pipeline_status(interaction.channel, "ai_pipeline_deploy"))
        else:
            await interaction.channel.send(f"AI 재배포 파이프라인 실행 실패. 에러 코드: {response.status_code}")

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.command(name="bot")
async def bot_command(ctx):
    view = PipelineView()
    await ctx.send("어떤 파이프라인을 실행할까요?", view=view)

bot.run(DISCORD_TOKEN)
