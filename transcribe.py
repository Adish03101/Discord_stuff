import os
import openai
from dotenv import load_dotenv

load_dotenv()
TRANSCRIPTS_DIR = 'transcripts'
os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)

openai.api_key = os.getenv('OPENAI_API_KEY')

async def save_transcript(filename, guild_id):
    try:
        with open(filename, 'rb') as audio_files:
            response = openai.Audio.transcribe(
                model="whisper-1",
                file=audio_files,
                response_format="text"
            )
        transcript = response['text'].strip()
        transcript_path = os.path.join(TRANSCRIPTS_DIR, f"{guild_id}_transcript.txt")
        with open(transcript_path, 'w') as f:
            f.write(transcript)
        print(f"Transcript saved to {transcript_path}")
        return transcript_path
    except Exception as e:
        print(f"Error saving transcript: {e}")
        return None