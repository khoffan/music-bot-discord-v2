import discord
from datetime import datetime
import yt_dlp as youtube_dl
from discord.ext import commands, tasks
import asyncio


intents = discord.Intents().all()
bot = commands.Bot(command_prefix="!", intents=intents)

notify_times = [5,6,7,8, 9, 10, 11, 12, 15, 17, 19]

@tasks.loop(minutes=1)
async def check_notify_message():
    now = datetime.now()
    # current_hour = now.hour
    current_minute = now.minute

    # ตรวจสอบว่าตอนนี้อยู่ในช่วงเวลาที่กำหนดหรือไม่
    if current_minute in notify_times:
        channel = bot.get_channel(1101501209015222344)
        print(channel)# เปลี่ยน YOUR_CHANNEL_ID เป็น ID ของช่องที่ต้องการ
        await channel.send(f'🔔 แจ้งเตือน: ตอนนี้เป็นเวลา {now.strftime("%H:%M")}')

song_queue = []

youtube_dl.utils.bug_reports_message = lambda: ''

ytdl_format_options = {
    'format': 'bestaudio/best',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'ytsearch',
    'source_address': '0.0.0.0' # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = ""

    @classmethod
    async def from_url(cls, search_item, *, loop=None, stream=False):
        try:
            loop = loop or asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(search_item, download=not stream))
            print(f"data {data}")
            if 'entries' in data:
                # take first item from a playlist
                data = data['entries'][0]
            filename = data['title'] if stream else ytdl.prepare_filename(data)
            print(f"filename {filename}")
            return filename
        except Exception as e:
            print(f"ERROR: {str(e)}")


@bot.event
async def on_ready():
    print("Bot is ready!")
    check_notify_message.start()


@bot.event
async def on_message(message):
    await bot.process_commands(message)

@bot.command(name='join', help='Joins a voice channel')
async def join(ctx):
    if not ctx.message.author.voice:
        await ctx.send("{} is not connected to a voice channel".format(ctx.message.author.name))
        return
    else:
        channel = ctx.message.author.voice.channel
    await channel.connect()

@bot.command(name='leave', help='Leaves the voice channel')
async def leave(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_connected():
        await voice_client.disconnect()
    else:
        await ctx.send("The bot is not connected to a voice channel.")


@bot.command(name='next')
async def play_next_song(ctx):
    try:
        if len(song_queue) > 0:
            next_song = song_queue.pop(0)
            voice_channel = ctx.message.guild.voice_client
            voice_channel.play(discord.FFmpegPCMAudio(executable="ffmpeg", source=next_song),
                               after=lambda e: asyncio.run_coroutine_threadsafe(play_next_song(ctx), bot.loop))
            await ctx.send('**Now playing:** {}'.format(next_song))
        else:
            await ctx.send('There are no songs in the queue')
    except Exception as e:
        print(e)
        await ctx.send("The bot is not connected to a voice channel.")



@bot.command(name='play', help='To play song')
async def play(ctx, *, search_item):
    # print(url)
    try:
        server = ctx.message.guild
        voice_channel = server.voice_client

        async with ctx.typing():
            song = await YTDLSource.from_url(search_item, loop=bot.loop)
            song_queue.append(song)
            await ctx.send(f"**Added to queue:** {song}")

        if not voice_channel.is_playing():
            await play_next_song(ctx)
    except Exception as e:
        print(e)
        await ctx.send("The bot is not connected to a voice channel.")


@bot.command()
async def show_queue(ctx):
    await ctx.send(song_queue)

@bot.command()
async def skip(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_playing():
        voice_client.stop()
        await ctx.send("Skipped!")
        await play_next_song(ctx)
    else:
        await ctx.send("The bot is not playing anything at the moment.")

@bot.command(name='pause', help='This command pauses the song')
async def pause(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_playing():
        await voice_client.pause()
    else:
        await ctx.send("The bot is not playing anything at the moment.")


@bot.command(name='resume', help='Resumes the song')
async def resume(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_paused():
        await voice_client.resume()
    else:
        await ctx.send("The bot was not playing anything before this. Use play_song command")


@bot.command(name='stop', help='Stops the song')
async def stop(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_playing():
        await voice_client.stop()
    else:
        await ctx.send("The bot is not playing anything at the moment.")




if __name__ == "__main__":
    bot.run("your-token-here")