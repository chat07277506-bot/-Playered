import discord
from discord import app_commands
from discord.ext import commands
import asyncio
from aiohttp import web
import yt_dlp
import random
import os

# ==============================================================================
# [랜더 무료 웹 서비스 우회용 미니 웹 서버]
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
# [유튜브 오디오 스트리밍 설정 (yt-dlp) - 차단 우회 스푸핑 추가]
# ==============================================================================
YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
    # 🌟 [클라우드 IP 차단 우회 핵심 옵션] 유튜브에게 모바일 앱(iOS/Android)인 척 속입니다.
    'extractor_args': {
        'youtube': {
            'player_client': ['ios', 'android'],
            'skip': ['dash', 'hls']
        }
    }
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=True):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        
        if 'entries' in data:
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        
        # static-ffmpeg 연동 경로 지정
        from static_ffmpeg import run
        ffmpeg_bin, _ = run.get_or_fetch_platform_executables_else_raise()
        
        return cls(discord.FFmpegPCMAudio(filename, executable=ffmpeg_bin, **FFMPEG_OPTIONS), data=data)

# ==============================================================================
# [Playered 메인 봇 클래스]
# ==============================================================================
class PlayeredBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.voice_states = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)
        self.music_queues = {}

    async def setup_hook(self):
        self.loop.create_task(start_web_server())
        await self.tree.sync()

    async def on_ready(self):
        print(f"Logged in as {self.user.name} (ID: {self.user.id})")
        print("Playered Bot is fully ready and error-free!")

bot = PlayeredBot()

def play_next(interaction: discord.Interaction, guild_id: int):
    if guild_id in bot.music_queues and bot.music_queues[guild_id]:
        next_song = bot.music_queues[guild_id].pop(0)
        vc = interaction.guild.voice_client
        if vc and vc.is_connected():
            vc.play(next_song['source'], after=lambda e: play_next(interaction, guild_id))
            bot.loop.create_task(interaction.channel.send(f"🎵 대기열의 다음 곡을 재생합니다: **{next_song['title']}**"))
    else:
        print("대기열이 비어있습니다.")

# ------------------------------------------------------------------------------
# 음악 관련 명령어들
# ------------------------------------------------------------------------------
@bot.tree.command(name="재생", description="유튜브 주소로 음악을 재생하거나 대기열에 추가합니다. (최대 10곡)")
@app_commands.describe(url="유튜브 영상 링크(URL)를 입력해주세요.")
async def play(interaction: discord.Interaction, url: str):
    await interaction.response.defer(ephemeral=False)
    
    if not interaction.user.voice:
        await interaction.followup.send("❌ 먼저 음성 채널에 입장한 뒤 명령어를 사용해 주세요!")
        return

    guild_id = interaction.guild.id
    if guild_id not in bot.music_queues:
        bot.music_queues[guild_id] = []

    if len(bot.music_queues[guild_id]) >= 10:
        await interaction.followup.send("⚠️ 대기열이 가득 찼습니다! (최대 10곡까지만 쌓아둘 수 있습니다.)")
        return

    try:
        player = await YTDLSource.from_url(url, loop=bot.loop, stream=True)
    except Exception as e:
        # 🌟 진짜 에러 원인이 무엇인지 렌더 로그창에 상세하게 출력하도록 보강했습니다.
        print(f"⚠️ [재생 에러 상세 로그]: {e}")
        await interaction.followup.send("❌ 음악 정보를 불러오는 중 에러가 발생했습니다. URL을 다시 확인해 주세요.")
        return

    vc = interaction.guild.voice_client
    if not vc:
        vc = await interaction.user.voice.channel.connect()

    if vc.is_playing():
        bot.music_queues[guild_id].append({'title': player.title, 'source': player})
        await interaction.followup.send(f" 대기열에 추가되었습니다: **{player.title}** (현재 대기: {len(bot.music_queues[guild_id])}곡)")
    else:
        vc.play(player, after=lambda e: play_next(interaction, guild_id))
        await interaction.followup.send(f"🎵 지금 재생합니다: **{player.title}**")

@bot.tree.command(name="정지", description="현재 곡을 정지하고 다음 대기열 곡이 있다면 재생합니다.")
async def stop(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc and vc.is_playing():
        vc.stop()
        await interaction.response.send_message("⏹️ 현재 재생 중인 곡을 정지했습니다.")
    else:
        await interaction.response.send_message("❌ 현재 재생 중인 음악이 없습니다.")

@bot.tree.command(name="재생목록", description="현재 대기열에 쌓여 있는 노래 제목 리스트를 보여줍니다.")
async def queue_list(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    if guild_id not in bot.music_queues or not bot.music_queues[guild_id]:
        await interaction.response.send_message("📭 현재 대기열에 남은 음악이 없습니다.")
        return

    embed = discord.Embed(title="📋 Playered 현재 재생 대기열", color=discord.Color.blue())
    for idx, song in enumerate(bot.music_queues[guild_id], start=1):
        embed.add_field(name=f"[{idx}번 곡]", value=song['title'], inline=False)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="재생목록제거", description="대기열에서 특정 번호의 곡을 삭제합니다.")
@app_commands.describe(번호="삭제하고 싶은 재생목록의 번호를 입력하세요.")
async def remove_queue(interaction: discord.Interaction, 번호: int):
    guild_id = interaction.guild.id
    if guild_id not in bot.music_queues or not bot.music_queues[guild_id]:
        await interaction.response.send_message("❌ 대기열이 비어 있어 제거할 수 없습니다.")
        return

    if 번호 < 1 or 번호 > len(bot.music_queues[guild_id]):
        await interaction.response.send_message(f"❌ 올바른 번호가 아닙니다.")
        return

    removed_song = bot.music_queues[guild_id].pop(번호 - 1)
    await interaction.response.send_message(f"🗑️ 대기열에서 **{removed_song['title']}**을(를) 제거했습니다.")

# ------------------------------------------------------------------------------
# 게임 내전 및 미니게임 관련 명령어들
# ------------------------------------------------------------------------------
@bot.tree.command(name="팀짜기", description="지정한 인원들을 원하는 개수의 팀으로 무작위 공평하게 나눕니다.")
@app_commands.describe(팀갯수="나누고 싶은 팀의 총 개수를 적어주세요.", 참여유저="참여할 친구들을 띄어쓰기나 멘션으로 입력해 주세요.")
async def match_team(interaction: discord.Interaction, 팀갯수: int, 참여유저: str):
    if 팀갯수 < 2:
        await interaction.response.send_message("❌ 팀은 최소 2개 이상으로만 짤 수 있습니다.")
        return

    user_list = [user.strip() for user in 참여유저.split(" ") if user.strip()]
    if len(user_list) < 팀갯수:
        await interaction.response.send_message("❌ 참여 유저 수가 설정한 팀의 개수보다 적습니다!")
        return

    random.shuffle(user_list)
    teams = {i: [] for i in range(1, 팀갯수 + 1)}
    for idx, user in enumerate(user_list):
        team_num = (idx % 팀갯수) + 1
        teams[team_num].append(user)

    embed = discord.Embed(title="🎮 인게임 내전 팀 구성 결과", color=discord.Color.green())
    for t_num, members in teams.items():
        embed.add_field(name=f"🚩 {t_num}팀", value=", ".join(members), inline=False)
        
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="주사위", description="설정한 최소값과 최대값 범위 내에서 무작위 숫자를 뽑아 굴립니다.")
@app_commands.describe(최소값="주사위의 최소 숫자를 지정하세요.", 최대값="주사위의 최대 숫자를 지정하세요.")
async def roll_dice(interaction: discord.Interaction, 최소값: int, 최대값: int):
    if 최소값 >= 최대값:
        await interaction.response.send_message("❌ 최소값은 최대값보다 작아야 유효합니다.")
        return

    result = random.randint(최소값, 최대값)
    await interaction.response.send_message(f"🎲 **주사위 굴리기 ({최소값} ~ {최대값})**\n🎯 결과: **{result}** 가 나왔습니다!")

@bot.tree.command(name="동전던지기", description="가벼운 내기용 앞/뒤 동전 던지기 결과를 출력합니다.")
async def flip_coin(interaction: discord.Interaction):
    result = random.choice(["🪙 앞면 (Head)", "🪙 뒷면 (Tail)"])
    await interaction.response.send_message(f" Toss! 동전을 던진 결과...\n👉 **{result}** 입니다!")

TOKEN = os.environ.get("DISCORD_TOKEN")
if TOKEN:
    bot.run(TOKEN)
else:
    print("❌ 환경 변수 'DISCORD_TOKEN'을 찾을 수 없습니다.")
