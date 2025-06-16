import os
from os import environ as env
from dotenv import load_dotenv
import discord
# from transcribe import save_transcript
import datetime

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
RECORDING_DIR = 'recordings'
discord.opus.load_opus("/lib/x86_64-linux-gnu/libopus.so.0")

from discord import opus

print("Is Opus loaded?", opus.is_loaded())

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
        await ctx.respond("⚠️ You are not in a voice channel.")
        return

    print("Voice state:", voice)
    print("Voice channel:", voice.channel)

    try:
        vc = await voice.channel.connect()
        print("✅ Connected to voice channel.")
        connections.update({ctx.guild.id: vc})

        vc.start_recording(
        discord.sinks.WaveSink(),  
        save_to_file,
        ctx.channel,
    )
        await ctx.respond("🔴 Listening to this conversation.")
    except Exception as e:
        await ctx.respond(f"❌ Error connecting: {e}")
        print(f"❌ Connection error: {e}")


async def save_to_file(sink, channel):
    if not os.path.exists(RECORDING_DIR):
        os.makedirs(RECORDING_DIR)

    if not sink.audio_data:
        await channel.send("⚠️ No audio was captured. Make sure someone spoke during the session.")
        return

    try:
        for user_id, audio in sink.audio_data.items():
            user = await channel.guild.fetch_member(user_id)
            filename = f"{RECORDING_DIR}/{channel.guild.id}_{user.display_name}_{user_id}.wav"

            with open(filename, "wb") as f:
                f.write(audio.file.getvalue())

            await channel.send(f"✅ Recording saved to: {filename}")

    except Exception as e:
        error_message = f"{datetime.datetime.now().isoformat()} - Error saving recording: {e}\n"
        with open("error.log", "a") as log_file:
            log_file.write(error_message)
        await channel.send(f"⚠️ Error saving recording: {e}")

    # await save_transcript(filename, channel.guild.id)



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
