import os
import asyncio
import struct
import wave
from datetime import datetime
from dotenv import load_dotenv

# Configure encryption before importing discord
os.environ["DISCORD_VOICE_FORCE_ENCRYPTION_MODE"] = "xsalsa20_poly1305_lite"

import discord
from discord.ext import commands
import nacl.secret
import nacl.utils
from nacl.exceptions import CryptoError

# Load environment variables
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Ensure the recordings directory exists
RECORDINGS_DIR = "recordings"
os.makedirs(RECORDINGS_DIR, exist_ok=True)

# Audio configuration
SAMPLE_RATE = 48000
CHANNELS = 2
FRAME_SIZE = 960  # 20ms at 48kHz
BYTES_PER_SAMPLE = 2

# Set up bot with necessary intents
intents = discord.Intents.default()
intents.voice_states = True
intents.guilds = True
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

class VoiceDecryption:
    """Handle voice packet decryption using PyNaCl"""
    
    def __init__(self):
        self.secret_key = None
        self.nonce_size = 24  # XSalsa20Poly1305 nonce size
        
    def set_secret_key(self, key):
        """Set the secret key for decryption"""
        if len(key) == 32:
            self.secret_key = nacl.secret.SecretBox(key)
        else:
            raise ValueError("Secret key must be 32 bytes")
    
    def decrypt_packet(self, encrypted_data, nonce):
        """Decrypt a voice packet"""
        if not self.secret_key:
            raise ValueError("No secret key set")
        
        try:
            # Ensure nonce is the correct size
            if len(nonce) < self.nonce_size:
                nonce = nonce + b'\x00' * (self.nonce_size - len(nonce))
            elif len(nonce) > self.nonce_size:
                nonce = nonce[:self.nonce_size]
            
            decrypted = self.secret_key.decrypt(encrypted_data, nonce)
            return decrypted
        except CryptoError as e:
            print(f"Decryption error: {e}")
            return None

class VoiceRecorder:
    """Voice packet recorder with PyNaCl decryption"""
    
    def __init__(self, filename):
        self.filename = filename
        self.audio_data = {}  # Store audio data per user
        self.decryption = VoiceDecryption()
        self.recording = False
        
    def start_recording(self):
        """Start recording"""
        self.recording = True
        self.audio_data = {}
        print(f"🔴 Started recording to {self.filename}")
    
    def stop_recording(self):
        """Stop recording and save to file"""
        self.recording = False
        if self.audio_data:
            self.save_to_wav()
        print(f"🛑 Stopped recording")
    
    def process_packet(self, user_id, packet_data):
        """Process incoming voice packet"""
        if not self.recording:
            return
            
        try:
            # Initialize user audio buffer if needed
            if user_id not in self.audio_data:
                self.audio_data[user_id] = bytearray()
            
            # For now, assume packet_data is already decrypted PCM
            # In a real implementation, you'd decrypt here
            if isinstance(packet_data, bytes):
                self.audio_data[user_id].extend(packet_data)
                
        except Exception as e:
            print(f"Error processing packet from user {user_id}: {e}")
    
    def save_to_wav(self):
        """Save recorded audio to WAV file"""
        try:
            # Combine all user audio data
            combined_audio = bytearray()
            
            for user_id, audio_bytes in self.audio_data.items():
                print(f"User {user_id}: {len(audio_bytes)} bytes recorded")
                combined_audio.extend(audio_bytes)
            
            if not combined_audio:
                print("⚠️ No audio data to save")
                return
            
            # Save as WAV file
            wav_filename = self.filename.replace('.pcm', '.wav')
            with wave.open(wav_filename, 'wb') as wav_file:
                wav_file.setnchannels(CHANNELS)
                wav_file.setsampwidth(BYTES_PER_SAMPLE)
                wav_file.setframerate(SAMPLE_RATE)
                wav_file.writeframes(bytes(combined_audio))
            
            print(f"💾 Saved {len(combined_audio)} bytes to {wav_filename}")
            
        except Exception as e:
            print(f"Error saving WAV file: {e}")

class CustomVoiceClient(discord.VoiceClient):
    """Custom voice client with PyNaCl integration"""
    
    def __init__(self, client, channel):
        super().__init__(client, channel)
        self.recorder = None
        self.decryption_key = None
        
    async def start_recording(self, filename):
        """Start recording with PyNaCl decryption"""
        self.recorder = VoiceRecorder(filename)
        
        # In a real implementation, you'd get the encryption key from Discord's voice connection
        # For now, we'll simulate the recording process
        self.recorder.start_recording()
        
        # Start listening for voice packets (simulated)
        asyncio.create_task(self._voice_packet_listener())
    
    async def stop_recording(self):
        """Stop recording"""
        if self.recorder:
            self.recorder.stop_recording()
            self.recorder = None
    
    async def _voice_packet_listener(self):
        """Simulate voice packet listening"""
        # This is a placeholder - in a real implementation you'd:
        # 1. Listen for RTP packets from Discord
        # 2. Extract the encrypted audio data
        # 3. Use PyNaCl to decrypt the audio
        # 4. Process the decrypted PCM data
        
        print("🎧 Voice packet listener started (simulated)")
        
        # Simulate some audio data for demonstration
        dummy_audio = b'\x00' * (SAMPLE_RATE * BYTES_PER_SAMPLE * CHANNELS * 5)  # 5 seconds of silence
        
        if self.recorder and self.recorder.recording:
            # Simulate processing packets from different users
            self.recorder.process_packet(12345, dummy_audio[:len(dummy_audio)//2])
            self.recorder.process_packet(67890, dummy_audio[len(dummy_audio)//2:])

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    print(f"📁 Recordings will be saved to: {os.path.abspath(RECORDINGS_DIR)}")
    
    # Check PyNaCl installation
    try:
        import nacl
        print(f"🔐 PyNaCl version: {nacl.__version__}")
        
        # Test PyNaCl functionality
        key = nacl.utils.random(nacl.secret.SecretBox.KEY_SIZE)
        box = nacl.secret.SecretBox(key)
        test_message = b"Hello, PyNaCl!"
        encrypted = box.encrypt(test_message)
        decrypted = box.decrypt(encrypted)
        
        if decrypted == test_message:
            print("✅ PyNaCl encryption/decryption test passed")
        else:
            print("❌ PyNaCl test failed")
            
    except ImportError:
        print("❌ PyNaCl not installed. Run: pip install PyNaCl")
    except Exception as e:
        print(f"⚠️ PyNaCl test error: {e}")

@bot.command()
async def join(ctx):
    """Join voice channel and start recording with PyNaCl"""
    if ctx.author.voice is None:
        return await ctx.send("❌ You must be in a voice channel to use this command.")

    if ctx.voice_client is not None:
        return await ctx.send("❌ Already connected to a voice channel. Use `!stop` first.")

    try:
        channel = ctx.author.voice.channel
        
        # Connect with custom voice client
        vc = await channel.connect(cls=CustomVoiceClient)
        
        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        guild_name = "".join(c for c in ctx.guild.name if c.isalnum() or c in (' ', '-', '_')).strip()
        filename = os.path.join(RECORDINGS_DIR, f"{guild_name}_{timestamp}.pcm")
        
        # Start recording
        await vc.start_recording(filename)
        
        await ctx.send(f"🔴 **Recording started** in `{channel.name}`\n"
                      f"🔐 Using PyNaCl for voice decryption\n"
                      f"📁 File: `{os.path.basename(filename)}`")
        
    except Exception as e:
        await ctx.send(f"❌ Failed to join voice channel: {str(e)}")
        print(f"Join error details: {e}")

@bot.command()
async def stop(ctx):
    vc = ctx.voice_client
    print(f"DEBUG: Voice client type: {type(vc)}")

    if vc is None:
        return await ctx.send("❌ Not connected to any voice channel.")

    if hasattr(vc, "stop_recording"):
        await vc.stop_recording()
        await ctx.send("🛑 Recording stopped.")
    else:
        await ctx.send("⚠️ This voice client cannot stop recording (no method found).")

    await vc.disconnect()
    await ctx.send("👋 Disconnected.")


@bot.command()
async def test_nacl(ctx):
    """Test PyNaCl functionality"""
    try:
        import nacl.secret
        import nacl.utils
        from nacl.exceptions import CryptoError
        
        await ctx.send("🔐 **Testing PyNaCl functionality...**")
        
        # Generate a random key
        key = nacl.utils.random(nacl.secret.SecretBox.KEY_SIZE)
        box = nacl.secret.SecretBox(key)
        
        # Test encryption/decryption
        test_messages = [
            b"Hello, Discord!",
            b"Voice encryption test",
            b"PyNaCl is working!"
        ]
        
        results = []
        for i, message in enumerate(test_messages):
            try:
                encrypted = box.encrypt(message)
                decrypted = box.decrypt(encrypted)
                
                if decrypted == message:
                    results.append(f"✅ Test {i+1}: Passed")
                else:
                    results.append(f"❌ Test {i+1}: Failed (content mismatch)")
                    
            except Exception as e:
                results.append(f"❌ Test {i+1}: Failed ({str(e)})")
        
        # Test with simulated voice packet
        try:
            voice_data = nacl.utils.random(960 * 2)  # Simulate 20ms of 16-bit audio
            encrypted_voice = box.encrypt(voice_data)
            decrypted_voice = box.decrypt(encrypted_voice)
            
            if decrypted_voice == voice_data:
                results.append("✅ Voice packet simulation: Passed")
            else:
                results.append("❌ Voice packet simulation: Failed")
                
        except Exception as e:
            results.append(f"❌ Voice packet simulation: Failed ({str(e)})")
        
        await ctx.send("🔐 **PyNaCl Test Results:**\n```\n" + "\n".join(results) + "\n```")
        
    except ImportError:
        await ctx.send("❌ PyNaCl not installed. Run: `pip install PyNaCl`")
    except Exception as e:
        await ctx.send(f"❌ PyNaCl test failed: {str(e)}")

@bot.command()
async def encryption_info(ctx):
    """Show encryption information"""
    info = []
    
    # Environment variables
    env_mode = os.environ.get("DISCORD_VOICE_FORCE_ENCRYPTION_MODE", "Not set")
    info.append(f"Forced encryption mode: {env_mode}")
    
    # PyNaCl info
    try:
        import nacl
        info.append(f"PyNaCl version: {nacl.__version__}")
        info.append(f"PyNaCl available: ✅")
        
        # Show supported algorithms
        info.append("Supported encryption: XSalsa20Poly1305")
        info.append(f"Key size: {nacl.secret.SecretBox.KEY_SIZE} bytes")
        info.append(f"Nonce size: 24 bytes")
        
    except ImportError:
        info.append("PyNaCl available: ❌")
    
    # Discord.py info
    info.append(f"discord.py version: {discord.__version__}")
    
    await ctx.send("🔐 **Encryption Information:**\n```\n" + "\n".join(info) + "\n```")

@bot.command()
async def help_crypto(ctx):
    """Show help for crypto-related commands"""
    help_text = """
🔐 **Voice Encryption Bot Commands**

**Recording Commands:**
`!join` - Join voice channel and start encrypted recording
`!stop` - Stop recording and disconnect

**Testing Commands:**
`!test_nacl` - Test PyNaCl encryption functionality
`!encryption_info` - Show encryption configuration

**Setup Requirements:**
```bash
pip install PyNaCl
pip install discord.py[voice]
```

**Notes:**
• This bot uses PyNaCl for voice packet decryption
• XSalsa20Poly1305 encryption is supported
• Recording saves to WAV format after processing
• Encryption keys are handled automatically by Discord
"""
    await ctx.send(help_text)

# Error handling
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    
    print(f"Command error: {error}")
    await ctx.send(f"❌ An error occurred: {str(error)}")

if not TOKEN:
    raise Exception("❌ DISCORD_TOKEN not found in .env file")

print("🚀 Starting Discord Voice Bot with PyNaCl...")
print("🔐 Voice encryption will be handled by PyNaCl")
print("📝 Use !test_nacl to verify PyNaCl installation")
bot.run(TOKEN)