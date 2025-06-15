import os
from os import environ as env
from dotenv import load_dotenv
import discord
from transcribe import save_transcript
load_dotenv()
TOKEN = os.getenv('DISCORD_BOT_TOKEN')
RECORDING_DIR = 'recordings'
discord.opus.load_opus("libopus.so.0")

intents = discord.Intents.default()
intents.voice_states = True
intents.guilds = True
intents.messages = True
intents.message_content = True

bot = discord.Bot(intents=intents)

connections = {}

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

@bot.command()
async def join(ctx):
    voice = ctx.author.voice
    if not voice:
        await ctx.respond("⚠️ You are not in a voice channel. Please join one")
        return

    vc = await voice.channel.connect()
    connections.update({ctx.guild.id: vc})

    vc.start_recording(
        discord.sinks.WaveSink(),
        save_to_file,
        ctx.channel,
    )
    await ctx.respond("🔴 Listening to this conversation.")

async def save_to_file(sink, channel):
    if not os.path.exists(RECORDING_DIR):
        os.makedirs(RECORDING_DIR)

    try:
        # Just get the first audio stream (from one speaker)
        audio = next(iter(sink.audio_data.values()))
        filename = f"{RECORDING_DIR}/{channel.guild.id}_recording.wav"

        with open(filename, "wb") as f:
            f.write(audio.file.getvalue())

        await channel.send(f"✅ Recording saved to: {filename}")

    except Exception as e:
        await channel.send(f"⚠️ Error saving recording: {e}")

    await save_transcript(filename, channel.guild.id)



@bot.command()
async def stop(ctx):
    if ctx.guild.id not in connections:
        await ctx.respond("⚠️ I am not connected to a voice channel.")
        return

    vc = connections[ctx.guild.id]
    if vc.is_connected():
        vc.stop_recording()
        await vc.disconnect()
        del connections[ctx.guild.id]
        await ctx.respond("🔴 Stopped recording and disconnected from the voice channel.")
    else:
        await ctx.respond("⚠️ I am not connected to a voice channel.")

bot.run(TOKEN)
