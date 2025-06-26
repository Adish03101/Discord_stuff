import os
from os import environ as env
from dotenv import load_dotenv
import discord
import traceback
from datetime import datetime, timedelta
from collections import defaultdict
import json
import wave
import contextlib

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
RECORDING_DIR = 'recordings'
LOG_FILE = 'recording_debug.log'

# Improved Opus loading with fallback
try:
    discord.opus.load_opus('libopus.so.0')  # Common Linux path
except OSError:
    try:
        discord.opus.load_opus('opus')  # Try default name
    except:
        print("⚠️ Opus not loaded - voice may not work")

print("Opus loaded:", discord.opus.is_loaded())

intents = discord.Intents.default()
intents.voice_states = True
intents.guilds = True
intents.messages = True
intents.message_content = True

bot = discord.Bot(intents=intents)
connections = {}

def log(message):
    timestamp = datetime.now().isoformat()
    print(f"[{timestamp}] {message}")
    with open(LOG_FILE, 'a') as f:
        f.write(f"[{timestamp}] {message}\n")

@bot.event
async def on_ready():
    log("Bot ready")
    print(f"✅ Logged in as {bot.user}")

class CustomWaveSink(discord.sinks.WaveSink):
    def __init__(self):
        super().__init__()
        self.time_segments = defaultdict(list)
        self.last_seen = {}
        self.user_id_map = {}
        self.speaker_counter = 1
        self.first_data_received = {}  # Track first data per user

    def write(self, data, user_id):
        """Fixed parameter order: (data, user_id)"""
        if user_id not in self.user_id_map:
            speaker_label = f"speaker_{len(self.user_id_map) + 1}"
            self.user_id_map[user_id] = speaker_label
            self.first_data_received[user_id] = datetime.now()

        speaker = self.user_id_map[user_id]
        now = datetime.now()

        # Initialize if first segment
        if user_id not in self.last_seen:
            self.time_segments[speaker].append({
                'start': self.first_data_received[user_id],
                'end': now
            })
            self.last_seen[user_id] = now
            super().write(data, user_id)
            return

        last = self.last_seen[user_id]
        gap = (now - last).total_seconds()

        # Extend segment if within 2s gap, else new segment
        if gap <= 2.0:
            self.time_segments[speaker][-1]['end'] = now
        else:
            # Insert silence segment
            self.time_segments[speaker].append({
                'start': last + timedelta(seconds=1),
                'end': now - timedelta(seconds=1),
                'silent': True
            })
            # New speech segment
            self.time_segments[speaker].append({
                'start': now,
                'end': now
            })

        self.last_seen[user_id] = now
        super().write(data, user_id)

    def get_timeline_data(self):
        return dict(self.time_segments)

@bot.command()
async def join(ctx):
    voice = ctx.author.voice
    if not voice:
        await ctx.respond("⚠️ Join a voice channel first")
        return

    try:
        vc = await voice.channel.connect()
        connections[ctx.guild.id] = vc
        
        session_id = f"{ctx.guild.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        vc.start_recording(
            CustomWaveSink(),
            lambda sink, channel: save_to_file(sink, channel, session_id),
            ctx.channel
        )
        await ctx.respond("🔴 Recording started")
    except Exception as e:
        log(f"Join error: {traceback.format_exc()}")
        await ctx.respond(f"❌ Error: {str(e)}")

async def save_to_file(sink, channel, session_id):
    os.makedirs(RECORDING_DIR, exist_ok=True)
    
    # 1. Save audio files
    for user_id, audio in sink.audio_data.items():
        try:
            user = await channel.guild.fetch_member(user_id)
            safe_name = "".join(c for c in user.display_name if c.isalnum() or c in ' _-').rstrip()
            filename = f"{RECORDING_DIR}/{session_id}_{safe_name}_{user_id}.wav"
            
            with open(filename, 'wb') as f:
                f.write(audio.file.getvalue())
            await channel.send(f"💾 Saved {safe_name}'s audio")
        except Exception as e:
            log(f"Save error for {user_id}: {traceback.format_exc()}")
    
    # 2. Save timeline with silence segments
    timeline = {
        user_id: [
            {
                'start': seg['start'].isoformat(),
                'end': seg['end'].isoformat(),
                'silent': seg.get('silent', False)
            } 
            for seg in segments
        ]
        for user_id, segments in sink.get_timeline_data().items()
    }
    
    timeline_path = f"{RECORDING_DIR}/{session_id}_timeline.json"
    with open(timeline_path, 'w') as f:
        json.dump(timeline, f, indent=2)
    
    await channel.send(f"⏱️ Timeline saved: `{timeline_path}`")

@bot.command()
async def stop(ctx):
    if ctx.guild.id not in connections:
        await ctx.respond("⚠️ Not recording")
        return

    vc = connections[ctx.guild.id]
    vc.stop_recording()
    await vc.disconnect()
    del connections[ctx.guild.id]
    await ctx.respond("⏹️ Recording stopped")

bot.run(TOKEN)
