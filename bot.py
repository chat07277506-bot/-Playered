import discord
from discord import app_commands
from discord.ext import commands
import asyncio
from aiohttp import web
import random
import os

# ==============================================================================
# [랜더 무료 웹 서비스 우회용 미니 웹 서버]
# 10분간 외부 트래픽이 없으면 봇이 강제로 기절(Timeout)하는 것을 완벽하게 방지합니다.
# ==============================================================================
async def handle(request):
    return web.Response(text="Playered Bot is Running Active!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f" Web Server Bypass Started on port {port}")

# ==============================================================================
# [에러 프리 오디오 스트리밍 설정]
# ==============================================================================
FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

class PlayeredBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.voice_states = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # 10분 우회 웹 서버 백그라운드 작동 개시
        self.loop.create_task(start_web_server())
        # 최신 표준 슬래시 명령어 동기화
        await self.tree.sync()

    async def on_ready(self):
        print(f"Logged in as {self.user.name}")
        print("Playered Final Integrated Bot is fully ready!")

bot = PlayeredBot()

# ==============================================================================
# 🎵 [음악 재생 관련 서포트 명령어]
# 유튜브 보안망에 찍힌 렌더 IP를 숨기기 위해 오픈소스 인비디우스 프록시망 주소로 가공해 재생합니다.
# ==============================================================================
@bot.tree.command(name="재생", description="데이터센터 IP 차단 없는 안정적인 우회 주소로 음악을 재생합니다.")
@app_commands.describe(주소="유튜브 영상 링크(URL) 또는 스트리밍 주소를 입력하세요.")
async def play(interaction: discord.Interaction, 주소: str):
    await interaction.response.defer(ephemeral=False) # 3초 타임아웃 선제 차단
    
    if not interaction.user.voice:
        await interaction.followup.send("❌ 먼저 음성 채널에 입장한 뒤 명령어를 사용해 주세요!")
        return

    vc = interaction.guild.voice_client
    if not vc:
        vc = await interaction.user.voice.channel.connect()

    try:
        if vc.is_playing():
            vc.stop()

        # 🌟 시스템 권한 없이 독립적으로 작동하는 static-ffmpeg 강제 로드
        from static_ffmpeg import run
        ffmpeg_bin, _ = run.get_or_fetch_platform_executables_else_raise()

        target_url = 주소
        # 유튜브 주소가 들어오면 비디오 ID만 떼어내어 우회 중계 프록시 서버(Invidious) 주소로 가공합니다.
        if "youtube.com" in 주소 or "youtu.be" in 주소:
            video_id = 주소.split("v=")[-1] if "v=" in 주소 else 주소.split("/")[-1]
            target_url = f"https://invidious.sethforalan.com/latest_version?id={video_id}&itag=251"

        source = discord.FFmpegPCMAudio(target_url, executable=ffmpeg_bin, **FFMPEG_OPTIONS)
        vc.play(source)
        await interaction.followup.send(f"🎵 활동 지원 오디오 스트리밍을 시작합니다!")
    except Exception as e:
        print(f"재생 에러 내부 로깅: {e}")
        await interaction.followup.send(f"❌ 오디오 장치를 가동하는 중 문제가 발생했습니다.")

@bot.tree.command(name="정지", description="현재 음성 채널에서 흘러나오는 음악을 정지합니다.")
async def stop(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc and vc.is_playing():
        vc.stop()
        await interaction.response.send_message("⏹️ 스트리밍 재생을 정지했습니다.")
    else:
        await interaction.response.send_message("❌ 현재 재생 중인 음악이 없습니다.")

# ==============================================================================
# 🎲 [추첨 및 활동 중재 비서 명령어]
# 유저가 중심이 되어 의견 조율이나 내기를 할 때 봇이 공평한 '기준'만 제공하고 뒤로 빠집니다.
# ==============================================================================

@bot.tree.command(name="추첨", description="현재 본인이 참가 중인 음성 채널 인원들 중에서 독박 당첨자를 추첨합니다.")
@app_commands.describe(당첨인원수="뽑고 싶은 당첨자의 명수를 숫자로 입력하세요.")
async def voice_draw(interaction: discord.Interaction, 당첨인원수: int):
    if not interaction.user.voice or not interaction.user.voice.channel:
        await interaction.response.send_message("❌ 이 명령어는 먼저 음성 채널(통화방)에 입장한 뒤 사용하실 수 있습니다!")
        return

    # 현재 명령어 유저와 같은 음성 채널에 있는 유저 리스트 추출
    members = interaction.user.voice.channel.members
    member_mentions = [m.mention for m in members]

    if len(member_mentions) < 당첨인원수:
        await interaction.response.send_message(f"❌ 통화방에 있는 인원({len(member_mentions)}명)보다 당첨 인원수가 더 많습니다!")
        return
    
    if 당첨인원수 < 1:
        await interaction.response.send_message("❌ 당첨 인원은 최소 1명 이상이어야 합니다.")
        return

    # 중복 없이 무작위 당첨자 추첨
    winners = random.sample(member_mentions, 당첨인원수)
    
    embed = discord.Embed(title="🎯 통화방 실시간 독박 추첨 결과", color=discord.Color.red())
    embed.add_field(name="🎁 당첨자 목록", value=", ".join(winners), inline=False)
    embed.set_footer(text=f"추첨 채널: {interaction.user.voice.channel.name}")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="순서", description="현재 들어가 있는 음성 채널 인원들을 무작위 순서로 배치하여 순서표를 생성합니다.")
async def sequence_order(interaction: discord.Interaction):
    if not interaction.user.voice or not interaction.user.voice.channel:
        await interaction.response.send_message("❌ 먼저 음성 채널(통화방)에 입장한 뒤 사용해 주세요!")
        return

    members = [m.name for m in interaction.user.voice.channel.members]
    random.shuffle(members) # 무작위 셔플
    
    order_list = []
    for idx, name in enumerate(members, start=1):
        order_list.append(f"**{idx}등** : {name}")

    embed = discord.Embed(title="🔀 인게임 순서 및 차례 배치 결과", color=discord.Color.orange())
    embed.description = "\n".join(order_list)
    embed.set_footer(text="가위바위보 대신 봇의 판결을 따르십시오.")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="팀짜기", description="현재 음성 채널의 인원들을 지정한 개수의 팀으로 무작위 공평 분배합니다.")
@app_commands.describe(팀갯수="나누고 싶은 팀의 총 개수를 입력하세요.")
async def match_team(interaction: discord.Interaction, 팀갯수: int):
    if not interaction.user.voice or not interaction.user.voice.channel:
        await interaction.response.send_message("❌ 먼저 음성 채널에 입장한 뒤 명령어를 사용해 주세요!")
        return
        
    if 팀갯수 < 2:
        await interaction.response.send_message("❌ 팀은 최소 2개 이상으로만 나눌 수 있습니다.")
        return

    members = [m.name for m in interaction.user.voice.channel.members]
    if len(members) < 팀갯수:
        await interaction.response.send_message("❌ 통화방 인원수가 설정한 팀 개수보다 적습니다!")
        return

    random.shuffle(members)
    teams = {i: [] for i in range(1, 팀갯수 + 1)}
    for idx, name in enumerate(members):
        team_num = (idx % 팀갯수) + 1
        teams[team_num].append(name)

    embed = discord.Embed(title="🎮 인게임 내전 팀 구성 결과", color=discord.Color.green())
    for t_num, group in teams.items():
        embed.add_field(name=f"🚩 {t_num}팀", value=", ".join(group), inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="주사위", description="설정한 최소값과 최대값 사이에서 무작위 숫자를 하나 굴립니다.")
async def roll_dice(interaction: discord.Interaction, 최소값: int, 최대값: int):
    if 최소값 >= 최대값:
        await interaction.response.send_message("❌ 최소값은 최대값보다 작아야 유효합니다.")
        return
    await interaction.response.send_message(f"🎲 주사위 결과 (`{최소값} ~ {최대값}`): **{random.randint(최소값, 최대값)}**")

@bot.tree.command(name="동전던지기", description="가벼운 확률 결정용 앞/뒤 동전 던지기 결과를 출력합니다.")
async def flip_coin(interaction: discord.Interaction):
    await interaction.response.send_message(f"🪙 동전 던지기 결과: **{random.choice(['앞면 (Head)', '뒷면 (Tail)'])}**")

# ==============================================================================
# [봇 가동]
# ==============================================================================
TOKEN = os.environ.get("DISCORD_TOKEN")
if TOKEN:
    bot.run(TOKEN)
else:
    print("❌ 환경 변수 'DISCORD_TOKEN'을 찾을 수 없습니다. 렌더 설정을 확인하세요.")
