import os
from os import environ as env
from dotenv import load_dotenv
import discord
import datetime
import traceback

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
RECORDING_DIR = 'recordings'
LOG_FILE = 'recording_debug.log'

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

def log(message):
    timestamp = datetime.datetime.now().isoformat()
    with open(LOG_FILE, 'a') as f:
        f.write(f"[{timestamp}] {message}\n")

@bot.event
async def on_ready():
    log("Bot is ready.")
    print(f"✅ Logged in as {bot.user}")

@bot.command()
async def join(ctx):
    log("join command triggered.")
    voice = ctx.author.voice
    if not voice:
        log("User not in a voice channel.")
        await ctx.respond("⚠️ You are not in a voice channel.")
        return

    log(f"Voice state: {voice}")
    log(f"Voice channel: {voice.channel}")

    try:
        vc = await voice.channel.connect()
        log("Connected to voice channel.")
        connections.update({ctx.guild.id: vc})

        vc.start_recording(
            discord.sinks.WaveSink(),  
            save_to_file,
            ctx.channel,
        )
        await ctx.respond("🔴 Listening to this conversation.")
        log("Recording started.")
    except Exception as e:
        err = traceback.format_exc()
        log(f"Error connecting: {e}\n{err}")
        await ctx.respond(f"❌ Error connecting: {e}")
        print(f"❌ Connection error: {e}")

async def save_to_file(sink, channel):
    log("save_to_file triggered.")

    if not os.path.exists(RECORDING_DIR):
        os.makedirs(RECORDING_DIR)
        log("Created recording directory.")

    if not sink.audio_data:
        log("No audio data found in sink.")
        await channel.send("⚠️ No audio was captured. Make sure someone spoke during the session.")
        return

    try:
        for user_id, audio in sink.audio_data.items():
            log(f"Saving audio for user_id: {user_id}")
            try:
                user = await channel.guild.fetch_member(user_id)
                log(f"Fetched user: {user.display_name} ({user.id})")
            except Exception as e:
                log(f"Failed to fetch member for user_id {user_id}: {e}")
                continue

            filename = f"{RECORDING_DIR}/{channel.guild.id}_{user.display_name}_{user_id}.wav"
            try:
                with open(filename, "wb") as f:
                    f.write(audio.file.getvalue())
                log(f"Audio saved for {user.display_name} at {filename}")
                await channel.send(f"✅ Recording saved to: {filename}")
            except Exception as e:
                err = traceback.format_exc()
                log(f"Error writing file for {user.display_name}: {e}\n{err}")
                await channel.send(f"⚠️ Error saving recording for {user.display_name}: {e}")
    except Exception as e:
        err = traceback.format_exc()
        log(f"General error in save_to_file: {e}\n{err}")
        await channel.send(f"⚠️ Error saving recording: {e}")

@bot.command()
async def stop(ctx):
    log("stop command triggered.")

    if ctx.guild.id not in connections:
        log("No active connection found for guild.")
        await ctx.respond("⚠️ I am not connected to a voice channel.")
        return

    vc = connections[ctx.guild.id]
    try:
        if vc.is_connected():
            vc.stop_recording()
            await vc.disconnect()
            del connections[ctx.guild.id]
            await ctx.respond("🔴 Stopped recording and disconnected from the voice channel.")
            log("Stopped recording and disconnected.")
        else:
            log("VC is not connected.")
            await ctx.respond("⚠️ I am not connected to a voice channel.")
    except Exception as e:
        err = traceback.format_exc()
        log(f"Error during stop command: {e}\n{err}")
        await ctx.respond(f"⚠️ Error stopping recording: {e}")

bot.run(TOKEN)
