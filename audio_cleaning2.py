import os
import json
from datetime import datetime, timedelta
from pydub.utils import which, mediainfo

# Set FFmpeg path
ffmpeg_path = which("ffmpeg")
if ffmpeg_path:
    print(f"Using FFmpeg at: {ffmpeg_path}")
else:
    print("Warning: FFmpeg not found")

log = []
speakers = {}
timeline = {}
overlaps = []

# Process files
for filename in os.listdir('recordings'):
    filepath = os.path.join('recordings', filename)
    print(f"\nProcessing file: {filepath}")
    
    if filename.endswith('.wav'):
        try:
            if not os.path.exists(filepath):
                print(f"File does not exist: {filepath}")
                continue
            file_size = os.path.getsize(filepath)
            print(f"File size: {file_size} bytes")
            if file_size == 0:
                print("File is empty")
                continue
            try:
                info = mediainfo(filepath)
                print(f"MediaInfo: {info}")
            except Exception as e:
                print(f"MediaInfo error: {e}")
            speaker_num = filename.split('_')[0]
            speaker_id = f"speaker_{speaker_num}"
            speakers[speaker_id] = filepath  # Only store path, not audio
            print(f"Loaded {speaker_id}")
        except Exception as e:
            print(f'Error processing {filename}: {e}')
            import traceback
            traceback.print_exc()
    elif filename.endswith('.json'):
        try:
            with open(filepath, 'r') as f:
                timeline = json.load(f)
            print(f"Timeline loaded with {len(timeline)} entries")
        except Exception as e:
            print(f'Error processing {filename}: {e}')

# 2. Convert ISO timestamps to milliseconds
all_starts = []
print("Speakers loaded:", list(speakers.keys()))
print("Timeline speakers:", list(timeline.keys()))

for sp, segments in timeline.items():
    if sp not in speakers:
        print(f"Skipping {sp} as no audio found")
        continue
    print(f"Speaker {sp} present in speakers.")
    for seg in segments:
        seg['start_dt'] = datetime.fromisoformat(seg['start'])
        seg['end_dt'] = datetime.fromisoformat(seg['end'])
        all_starts.append(seg['start_dt'])

time_zero = min(all_starts) if all_starts else datetime.now()

for sp, segments in timeline.items():
    for seg in segments:
        seg['start_ms'] = int((seg['start_dt'] - time_zero).total_seconds() * 1000)
        seg['end_ms'] = int((seg['end_dt'] - time_zero).total_seconds() * 1000)

# 3. Detect overlaps with detailed logging
def to_iso(dt):
    return dt.isoformat() if hasattr(dt, 'isoformat') else dt
speaker_list = list(timeline.keys())
for i in range(len(speaker_list)):
    for j in range(i + 1, len(speaker_list)):
        sp1, sp2 = speaker_list[i], speaker_list[j]
        for seg1 in timeline[sp1]:
            for seg2 in timeline[sp2]:
                if not seg1['silent'] and not seg2['silent']:
                    start = max(seg1['start_ms'], seg2['start_ms'])
                    end = min(seg1['end_ms'], seg2['end_ms'])
                    if start < end:
                        overlap_entry = {
                            'start_iso': (time_zero + timedelta(milliseconds=start)).isoformat(),
                            'end_iso': (time_zero + timedelta(milliseconds=end)).isoformat(),
                            'start_ms': start,
                            'end_ms': end,
                            'duration_ms': end - start,
                            'speakers': [sp1, sp2],
                            'segment1': {
                                'start': to_iso(seg1['start']),
                                'end': to_iso(seg1['end']),
                                'silent': seg1['silent'],
                                'start_ms': seg1['start_ms'],
                                'end_ms': seg1['end_ms']
                            },
                            'segment2': {
                                'start': to_iso(seg2['start']),
                                'end': to_iso(seg2['end']),
                                'silent': seg2['silent'],
                                'start_ms': seg2['start_ms'],
                                'end_ms': seg2['end_ms']
                            }
                        }
                        overlaps.append(overlap_entry)
                        log.append(f"Overlap detected: {sp1} and {sp2} from {overlap_entry['start_iso']} to {overlap_entry['end_iso']}")

# 4. (Audio processing removed)

# 5. (Audio appending removed)

# 6. (Audio export removed)

# 7. Save detailed log
with open("processing_log.txt", "w") as f:
    f.write("\n".join(log))

# 8. Save overlap details with serialized datetime
overlap_details_serializable = []
for ov in overlaps:
    ov_copy = ov.copy()
    ov_copy['segment1'] = ov['segment1'].copy()
    ov_copy['segment2'] = ov['segment2'].copy()
    for key in ['start_dt', 'end_dt']:
        if key in ov_copy['segment1']:
            ov_copy['segment1'][key] = ov_copy['segment1'][key].isoformat()
        if key in ov_copy['segment2']:
            ov_copy['segment2'][key] = ov_copy['segment2'][key].isoformat()
    overlap_details_serializable.append(ov_copy)

with open("overlap_details.json", "w") as f:
    json.dump({
        'overlaps': overlap_details_serializable,
        'late_segments': []  # No late segments since audio processing is removed
    }, f, indent=2)

print("Processing complete. (Audio processing removed)")
print(f"Detected {len(overlaps)} overlaps")
