import os
import json
from pydub import AudioSegment
from datetime import datetime, timedelta

# Initialize data structures
log = []
speakers = {}
timeline = {}
overlaps = []

# 1. Load audio files and timeline JSON
for i, x in enumerate(os.listdir('recordings')):
    if x.endswith('.wav'):
        try:
            # Initialize list for speaker if not exists
            if f'speaker_{i}' not in speakers:
                speakers[f'speaker_{i}'] = []
            speakers[f'speaker_{i}'].append(AudioSegment.from_file(f'recordings/{x}'))
        except Exception as e:
            print(f'Error processing {x}: {e}')
    elif x.endswith('.json'):
        try:
            with open(f'recordings/{x}', 'r') as f:
                timeline = json.load(f)
        except Exception as e:
            print(f'Error processing {x}: {e}')

# 2. Convert ISO timestamps to milliseconds
all_starts = []
for sp, segments in timeline.items():
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
speaker_list = list(timeline.keys())
for i in range(len(speaker_list)):
    for j in range(i+1, len(speaker_list)):
        sp1, sp2 = speaker_list[i], speaker_list[j]
        for seg1 in timeline[sp1]:
            for seg2 in timeline[sp2]:
                if not seg1['silent'] and not seg2['silent']:
                    start = max(seg1['start_ms'], seg2['start_ms'])
                    end = min(seg1['end_ms'], seg2['end_ms'])
                    if start < end:
                        # Create detailed overlap entry
                        overlap_entry = {
                            'start_iso': (time_zero + timedelta(milliseconds=start)).isoformat(),
                            'end_iso': (time_zero + timedelta(milliseconds=end)).isoformat(),
                            'start_ms': start,
                            'end_ms': end,
                            'duration_ms': end - start,
                            'speakers': [sp1, sp2],
                            'segment1': seg1,
                            'segment2': seg2
                        }
                        overlaps.append(overlap_entry)
                        log.append(f"Overlap detected: {sp1} and {sp2} from {overlap_entry['start_iso']} to {overlap_entry['end_iso']}")

# 4. Process segments with overlap handling
main_mix = AudioSegment.silent(duration=0)
late_speaker_segments = []

for sp, segments in timeline.items():
    for seg in segments:
        if not seg['silent']:
            audio = speakers[sp][0][seg['start_ms']:seg['end_ms']]  # [0] assumes first segment
            overlap_occurred = False
            
            for ov in overlaps:
                if sp in ov['speakers']:
                    # Check if this segment overlaps with this particular overlap
                    if seg['start_ms'] < ov['end_ms'] and seg['end_ms'] > ov['start_ms']:
                        overlap_occurred = True
                        # Determine if this speaker is the "later" one
                        is_later_speaker = (sp == ov['speakers'][1])
                        
                        if is_later_speaker:
                            # Cut overlapping portion
                            late_start = max(seg['start_ms'], ov['start_ms'])
                            late_end = min(seg['end_ms'], ov['end_ms'])
                            
                            if late_start < late_end:
                                # Save overlapping part for later
                                late_segment = speakers[sp][0][late_start:late_end]
                                late_speaker_segments.append({
                                    'segment': late_segment,
                                    'speaker': sp,
                                    'original_start': seg['start_dt'],
                                    'original_end': seg['end_dt'],
                                    'overlap_start': time_zero + timedelta(milliseconds=late_start),
                                    'overlap_end': time_zero + timedelta(milliseconds=late_end)
                                })
                                
                                # Add non-overlapping parts to main mix
                                if seg['start_ms'] < late_start:
                                    main_mix += speakers[sp][0][seg['start_ms']:late_start]
                                if late_end < seg['end_ms']:
                                    main_mix += speakers[sp][0][late_end:seg['end_ms']]
                            else:
                                main_mix += audio
                        else:
                            # For non-later speaker, add entire segment
                            main_mix += audio
                        break
            
            if not overlap_occurred:
                main_mix += audio

# 5. Append cut segments to end
for late in late_speaker_segments:
    main_mix += late['segment']
    log.append(f"Appended late segment for {late['speaker']} (original: {late['original_start'].isoformat()}-{late['original_end'].isoformat()})")

# 6. Export results
main_mix.export("combined.wav", format="wav")

# Save detailed log
with open("processing_log.txt", "w") as f:
    f.write("\n".join(log))

with open("overlap_details.json", "w") as f:
    json.dump({
        'overlaps': overlaps,
        'late_segments': [
            {
                'speaker': l['speaker'],
                'original_start': l['original_start'].isoformat(),
                'original_end': l['original_end'].isoformat(),
                'overlap_start': l['overlap_start'].isoformat(),
                'overlap_end': l['overlap_end'].isoformat(),
                'duration_ms': (l['overlap_end'] - l['overlap_start']).total_seconds() * 1000
            } for l in late_speaker_segments
        ]
    }, f, indent=2)

print("Processing complete. Combined audio saved as combined.wav")
print(f"Detected {len(overlaps)} overlaps")
print(f"Appended {len(late_speaker_segments)} late segments")
