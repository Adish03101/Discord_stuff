import os
import json
from pydub import AudioSegment
from datetime import datetime

from pydub.utils import which

# Set FFmpeg path
ffmpeg_path = which("ffmpeg")
if ffmpeg_path:
    AudioSegment.converter = ffmpeg_path
    print(f"Using FFmpeg at: {ffmpeg_path}")
else:
    print("Warning: FFmpeg not found")

def load_audio_files():
    """Load audio files with proper error handling"""
    speakers = {}
    for filename in os.listdir('recordings'):
        if filename.endswith('.wav'):
            filepath = os.path.join('recordings', filename)
            try:
                if not os.path.exists(filepath):
                    print(f"File does not exist: {filepath}")
                    continue
                file_size = os.path.getsize(filepath)
                if file_size == 0:
                    print(f"File is empty: {filepath}")
                    continue
                speaker_num = filename.split('_')[0]
                speaker_id = f"speaker_{speaker_num}"
                try:
                    audio = AudioSegment.from_wav(filepath)
                except:
                    try:
                        audio = AudioSegment.from_file(filepath, format="wav")
                    except:
                        audio = AudioSegment.from_file(filepath)
                speakers[speaker_id] = audio
                print(f"✅ Loaded {speaker_id}: {len(audio):,} ms ({len(audio)/1000:.2f}s)")
            except Exception as e:
                print(f'❌ Error processing {filename}: {e}')
    return speakers

def load_timeline():
    """Load timeline JSON file"""
    timeline = {}
    for filename in os.listdir('recordings'):
        if filename.endswith('.json'):
            filepath = os.path.join('recordings', filename)
            try:
                with open(filepath, 'r') as f:
                    timeline = json.load(f)
                print(f"✅ Timeline loaded from {filename} with {len(timeline)} speakers")
                break
            except Exception as e:
                print(f'❌ Error loading {filename}: {e}')
    return timeline

def create_natural_conversation_mix(speakers, timeline, max_gap_seconds=2.0):
    """
    Create natural conversation flow with minimal silence gaps.
    """
    all_speech_events = []
    audio_positions = {sp: 0 for sp in speakers.keys()}
    for speaker, segments in timeline.items():
        if speaker not in speakers:
            continue
        for seg in segments:
            if not seg['silent']:
                start_dt = datetime.fromisoformat(seg['start'])
                end_dt = datetime.fromisoformat(seg['end'])
                duration_ms = int((end_dt - start_dt).total_seconds() * 1000)
                all_speech_events.append({
                    'speaker': speaker,
                    'start_dt': start_dt,
                    'end_dt': end_dt,
                    'duration_ms': duration_ms
                })
    all_speech_events.sort(key=lambda x: x['start_dt'])
    conversation_mix = AudioSegment.silent(duration=0)
    overlap_segments = []
    for i, event in enumerate(all_speech_events):
        speaker = event['speaker']
        duration_ms = event['duration_ms']
        start_pos = audio_positions[speaker]
        end_pos = start_pos + duration_ms
        audio_chunk = speakers[speaker][start_pos:end_pos]
        audio_positions[speaker] = end_pos
        is_overlap = False
        if i > 0:
            prev_event = all_speech_events[i-1]
            if event['start_dt'] < prev_event['end_dt']:
                is_overlap = True
                prev_dur = int((prev_event['end_dt'] - prev_event['start_dt']).total_seconds() * 1000)
                if duration_ms <= prev_dur:
                    overlap_segments.append({'audio': audio_chunk, 'speaker': speaker})
                    continue
        if not is_overlap and i > 0:
            prev_event = all_speech_events[i-1]
            gap_seconds = (event['start_dt'] - prev_event['end_dt']).total_seconds()
            if gap_seconds > 0:
                actual_gap = min(gap_seconds, max_gap_seconds)
                gap_ms = int(actual_gap * 1000)
                if gap_ms > 0:
                    silence_gap = AudioSegment.silent(duration=gap_ms)
                    conversation_mix += silence_gap
        conversation_mix += audio_chunk
    for overlap in overlap_segments:
        conversation_mix += overlap['audio']
    return conversation_mix

def main():
    print("🎙️  DISCORD AUDIO PROCESSING — NATURAL CONVERSATION FLOW")
    print("=" * 60)
    print("\n1. 📁 LOADING AUDIO FILES:")
    speakers = load_audio_files()
    if not speakers:
        print("❌ No audio files loaded!")
        return
    print("\n2. 📋 LOADING TIMELINE:")
    timeline = load_timeline()
    if not timeline:
        print("❌ No timeline loaded!")
        return
    print("\n3. 🛠️  BUILDING NATURAL CONVERSATION MIX:")
    conversation_mix = create_natural_conversation_mix(speakers, timeline, max_gap_seconds=2.0)
    print("\n4. 💾 SAVING RESULT:")
    if len(conversation_mix) > 0:
        conversation_mix.export("natural_conversation.wav", format="wav")
        print(f"   ✅ Saved natural_conversation.wav ({len(conversation_mix):,}ms / {len(conversation_mix)/1000:.2f}s)")
        print("   🎉 SUCCESS: Audio processing completed!")
    else:
        print("   ❌ FAILURE: Combined track is 0ms")
    return conversation_mix

if __name__ == "__main__":
    main()
