import os
from os import environ as env
from dotenv import load_dotenv
import discord
import traceback
from datetime import datetime, timedelta
from collections import defaultdict
import json

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
    timestamp = datetime.now().isoformat()
    with open(LOG_FILE, 'a') as f:
        f.write(f"[{timestamp}] {message}\n")

@bot.event
async def on_ready():
    log("Bot is ready.")
    print(f"✅ Logged in as {bot.user}")


time_line = {}

#custom wavesink
class CustomWaveSink(discord.sinks.WaveSink):
    def __init__(self):
        super().__init__()
        self.time_segments = defaultdict(list)  # {user_id: [{'start': ..., 'end': ...}, ...]}
        self.last_seen = {}  # {user_id: datetime}

    def write(self, user_id, data):
        now = datetime.now()
        last = self.last_seen.get(user_id)

        # If silence > 2 sec, treat it as a new segment
        if last is None or (now - last) > timedelta(seconds=2):
            self.time_segments[user_id].append({'start': now, 'end': now})
        else:
            self.time_segments[user_id][-1]['end'] = now

        self.last_seen[user_id] = now
        super().write(user_id, data)

    def get_timeline_data(self):
        return self.time_segments
    

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

        session_id = f"{ctx.guild.id}_{ctx.author.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"        
        vc.start_recording(
            CustomWaveSink(),  
            lambda sinks, channel: save_to_file(sinks, channel, session_id),
            ctx.channel
        )
        await ctx.respond("🔴 Listening to this conversation.")
        log("Recording started.")
    except Exception as e:
        err = traceback.format_exc()
        log(f"Error connecting: {e}\n{err}")
        await ctx.respond(f"❌ Error connecting: {e}")
        print(f"❌ Connection error: {e}")

async def save_to_file(sink, channel, session_id):
    log("save_to_file triggered.")

    if not os.path.exists(RECORDING_DIR):
        os.makedirs(RECORDING_DIR)
        log("Created recording directory.")

    if not sink.audio_data:
        log("No audio data found in sink.")
        await channel.send("⚠️ No audio was captured. Make sure someone spoke during the session.")
        return

    # Retrieve segmented timeline from CustomWaveSink
    timeline = sink.get_timeline_data()

    try:
        for user_id, audio in sink.audio_data.items():
            log(f"Saving audio for user_id: {user_id}")

            try:
                user = await channel.guild.fetch_member(user_id)
                display_name = ''.join(c for c in user.display_name if c.isalnum() or c in (' ', '_')).strip()
                log(f"Fetched user: {display_name} ({user.id})")
            except Exception as e:
                display_name = str(user_id)
                log(f"Failed to fetch member for user_id {user_id}: {e}")
                continue

            filename = f"{RECORDING_DIR}/{session_id}_{display_name}_{user_id}.wav"
            try:
                with open(filename, "wb") as f:
                    f.write(audio.file.getvalue())
                log(f"Audio saved for {display_name} at {filename}")
                await channel.send(f"✅ Recording saved to: `{filename}`")
            except Exception as e:
                err = traceback.format_exc()
                log(f"Error writing file for {display_name}: {e}\n{err}")
                await channel.send(f"⚠️ Error saving recording for {display_name}: {e}")

        # Save the segmented timeline as JSON
        timeline_path = os.path.join(RECORDING_DIR, f"{session_id}_timeline.json")
        with open(timeline_path, "w") as f:
            json.dump(timeline, f, indent=2, default=str)
        log(f"Timeline saved at {timeline_path}")
        await channel.send(f"🕓 Timeline saved to `{timeline_path}`")

    except Exception as e:
        err = traceback.format_exc()
        log(f"General error in save_to_file: {e}\n{err}")
        await channel.send(f"⚠️ Error saving recording: {e}")

    print("Time line data:", timeline)

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
