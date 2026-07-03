import discord
from discord import app_commands
from discord.ext import commands
from aiohttp import web
import random
import os

# ==============================================================================
# [웹 서버 우회: 랜더 서버 잠자기 방지]
# ==============================================================================
async def handle(request):
    return web.Response(text="Playered Bot is Running!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

class PlayeredBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        self.loop.create_task(start_web_server())
        await self.tree.sync()

    async def on_ready(self):
        print(f"Logged in as {self.user.name}. Playered Bot Ready.")

bot = PlayeredBot()

# ==============================================================================
# [직접 입력 방식의 활동 서포트 명령어]
# ==============================================================================

@bot.tree.command(name="팀짜기", description="지정한 유저들을 무작위로 팀을 나눕니다.")
@app_commands.describe(팀갯수="나눌 팀 개수", 유저목록="유저 이름/멘션을 띄어쓰기로 구분하여 입력")
async def match_team(interaction: discord.Interaction, 팀갯수: int, 유저목록: str):
    members = [u.strip() for u in 유저목록.split(" ") if u.strip()]
    if len(members) < 팀갯수:
        await interaction.response.send_message("❌ 유저 수가 팀 개수보다 적습니다!", ephemeral=True)
        return

    random.shuffle(members)
    teams = {i: [] for i in range(1, 팀갯수 + 1)}
    for idx, name in enumerate(members):
        teams[(idx % 팀갯수) + 1].append(name)

    embed = discord.Embed(title="🎮 내전 팀 구성 결과", color=discord.Color.green())
    for t_num, group in teams.items():
        embed.add_field(name=f"🚩 {t_num}팀", value=", ".join(group), inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="추첨", description="입력한 유저들 중 독박 당첨자를 뽑습니다.")
@app_commands.describe(당첨인원수="뽑을 인원 수", 유저목록="유저 이름/멘션을 띄어쓰기로 구분하여 입력")
async def draw_user(interaction: discord.Interaction, 당첨인원수: int, 유저목록: str):
    members = [u.strip() for u in 유저목록.split(" ") if u.strip()]
    if len(members) < 당첨인원수:
        await interaction.response.send_message("❌ 참여 인원이 당첨 인원수보다 적습니다!", ephemeral=True)
        return

    winners = random.sample(members, 당첨인원수)
    embed = discord.Embed(title="🎯 독박 당첨 결과", color=discord.Color.red())
    embed.add_field(name="🎁 당첨자", value=", ".join(winners))
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="순서", description="입력한 유저들의 무작위 차례를 정합니다.")
@app_commands.describe(유저목록="유저 이름/멘션을 띄어쓰기로 구분하여 입력")
async def sequence_order(interaction: discord.Interaction, 유저목록: str):
    members = [u.strip() for u in 유저목록.split(" ") if u.strip()]
    random.shuffle(members)
    order_list = [f"**{idx}등** : {name}" for idx, name in enumerate(members, start=1)]
    
    embed = discord.Embed(title="🔀 무작위 차례 배치", description="\n".join(order_list), color=discord.Color.orange())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="내전공지", description="깔끔한 포맷의 내전 공지를 생성합니다.")
async def match_notice(interaction: discord.Interaction, 종목: str, 시간: str, 규칙: str):
    embed = discord.Embed(title=f"📢 {종목} 내전 매치", color=discord.Color.blue())
    embed.add_field(name="⏰ 시간", value=시간, inline=False)
    embed.add_field(name="📜 규칙", value=규칙, inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="주사위", description="숫자 범위를 정해 굴립니다.")
async def roll_dice(interaction: discord.Interaction, 최소값: int, 최대값: int):
    await interaction.response.send_message(f"🎲 결과: **{random.randint(최소값, 최대값)}**")

@bot.tree.command(name="동전던지기", description="앞면 혹은 뒷면을 결정합니다.")
async def flip_coin(interaction: discord.Interaction):
    await interaction.response.send_message(f"🪙 결과: **{random.choice(['앞면 (Head)', '뒷면 (Tail)'])}**")

# ==============================================================================
# [봇 실행]
# ==============================================================================
TOKEN = os.environ.get("DISCORD_TOKEN")
bot.run(TOKEN)
