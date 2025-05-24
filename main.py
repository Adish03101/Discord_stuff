import os
# os.environ["DISCORD_VOICE_FORCE_ENCRYPTION_MODE"] = "xsalsa20_poly1305"
from datetime import datetime
from dotenv import load_dotenv
import discord
from discord.ext import commands
from discord.ext.voice_recv import VoiceRecvClient
from discord.ext.voice_recv import AudioSink
import wave

# Load token
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Create recordings directory
RECORDINGS_DIR = "recordings"
os.makedirs(RECORDINGS_DIR, exist_ok=True)

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.guilds = True
bot = commands.Bot(command_prefix="!", intents=intents)

class MultiUserWaveSink(AudioSink):
    def __init__(self, folder_path):
        super().__init__()
        self.wave_files = {}
        self.filenames = {}  # Track filenames for reporting


    def write(self, user, data):
        try:
            if user.id not in self.wave_files:
                safe_name = "".join(c for c in user.name if c.isalnum() or c in (' ', '-', '_')).strip()
                if not safe_name:
                    safe_name = f"user_{user.id}"
                # Add timestamp to filename for uniqueness
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = os.path.join(RECORDINGS_DIR, f"{safe_name}_{user.id}_{timestamp}.wav")
                wf = wave.open(filename, 'wb')
                wf.setnchannels(2)
                wf.setsampwidth(2)
                wf.setframerate(48000)
                self.wave_files[user.id] = wf
                self.filenames[user.id] = filename
                print(f"📝 Started recording for {user.name} ({user.id}) -> {filename}")

            self.wave_files[user.id].writeframes(data.pcm)
        except Exception as e:
            print(f"⚠️ Error writing audio for {user}: {e}")
    def cleanup(self):
        print("🧹 Cleaning up wave files...")
        for user_id, wf in self.wave_files.items():
            wf.close()
            print(f"✅ Closed file for user {user_id}")

    def wants_opus(self) -> bool:
        return False

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    print(f"🎙 Recordings will be saved to: {os.path.abspath(RECORDINGS_DIR)}")

@bot.command()
async def join(ctx):
    """Join the voice channel and start recording with WaveSink."""
    if not ctx.author.voice:
        return await ctx.send("❌ Please join a voice channel first.")

    vc = await ctx.author.voice.channel.connect(cls=VoiceRecvClient)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    guild_name = "".join(c for c in ctx.guild.name if c.isalnum() or c in (' ', '-', '_')).strip()
    if not guild_name:  # Fallback if guild name is empty after cleaning
        guild_name = f"guild_{ctx.guild.id}"
    
    folder_path = os.path.join(RECORDINGS_DIR, f"{guild_name}_{timestamp}")

    # Create WaveSink with folder path
    try:
        sink = MultiUserWaveSink(folder_path)
        vc.listen(sink)
        vc.sink = sink  # Store reference for later
        print(f"🎙 Recording sink created for folder: {folder_path}")
    except Exception as e:
        await ctx.send(f"❌ Error starting recording: {e}")
        await vc.disconnect()
        return
    await ctx.send(f"🔴 Recording started in `{ctx.author.voice.channel.name}`.\nFiles will be saved to: `{folder_path}`")

@bot.command()
async def stop(ctx):
    """Stop recording and disconnect the bot."""
    vc = ctx.voice_client
    if vc is None or not hasattr(vc, "sink"):
        return await ctx.send("❌ Not recording.")

    vc.stop_listening()
    
    # Get list of saved files before cleanup
    saved_files = []
    if hasattr(vc, "sink") and hasattr(vc.sink, "filenames"):
        saved_files = list(vc.sink.filenames.values())
        print(f"DEBUG: saved_files = {saved_files}")  # Add this line
        vc.sink.cleanup()

    await vc.disconnect()

    if saved_files:
        file_list = "\n".join([os.path.basename(f) for f in saved_files])
        await ctx.send(f"🛑 Recording stopped.\nSaved files:\n```\n{file_list}\n```")
        print("📁 All files saved successfully:")
        for f in saved_files:
            print(f"  - {f}")
    else:
        await ctx.send("🛑 Recording stopped. No audio files were created.\n💡 Make sure users are speaking and have their microphones enabled.")

# Run the bot
if not TOKEN:
    raise Exception("❌ DISCORD_TOKEN not found in .env file")

bot.run(TOKEN)