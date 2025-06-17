from pydub import AudioSegment, silence
import os
from pydub.silence import detect_silence

# MIN_SILENCE_THRESH = -40
# MIN_SILENCE_LEN = 1000
# AUDIO_FOLDER = 'recordings'

# def split_audio_on_silence(audio_file):
#     audio = AudioSegment.from_file(audio_file)
#     segments = silence.split_on_silence(
#         audio,
#         min_silence_len=MIN_SILENCE_LEN,
#         silence_thresh=MIN_SILENCE_THRESH
#     )

class Audiosegment():
    def __init__(self, audio_file):
        self.audio = AudioSegment.from_file(audio_file)
    def split_on_silence(self, min_silence_len=1000, silence_thresh=-40):
        return detect_silence(
            self.audio,
            min_silence_len=min_silence_len,
            silence_thresh=silence_thresh
        )
    #the output is [...,(start_time, end_time), ...]

    def save_time(self, time_line_data, output_file):
        with open(output_file, 'w') as f:
            f.write("[")
            for start, end in time_line_data:
                f.write(f"start:{start}, end:{end}\n")
            f.write("]\n")
        print(f"Time line data saved to {output_file}")
    
    def process_audio(self, min_silence_len=1000, silence_thresh=-40, output_folder='output',i=1):
        
        try:
            non_silent = self.split_on_silence(min_silence_len, silence_thresh)
            audio_silent = AudioSegment.empty()
            silent_parts_times = []

            for i, (start_time, end_time) in enumerate(non_silent):
                if i == 0:
                    silent_start_times = 0
                else:
                    #silence start time is i-1 ka end time
                    silent_start_times = non_silent[i-1][1]
                silent_end_time = start_time
                audio_silent += self.audio[silent_start_times:silent_end_time]
                silent_parts_times.append((silent_start_times, silent_end_time))
            if not os.path.exists(output_folder):
                os.makedirs(output_folder)
            silent_text_path = os.path.join(output_folder, f'silent_parts.txt{i}')
            self.save_time(silent_parts_times, silent_text_path)
            print(f"Processed audio saved to and time data to {silent_text_path}")
        except Exception as e:
            print(f"An error occurred while processing the audio: {e}")

AUDIO_FOLDER = 'recordings'
def process_all_audio_files(folder=AUDIO_FOLDER):
    if not os.path.exists(folder):
        print(f"Folder {folder} does not exist.")
        return
    
    for i, filename in enumerate(os.listdir(folder)):
        if filename.endswith('.wav') or filename.endswith('.mp3'):
            audio_file_path = os.path.join(folder, filename)
            print(f"Processing {audio_file_path}...")
            audio_segment = Audiosegment(audio_file_path)
            output_folder = os.path.join(folder, f'time_stamps-{filename}')
            os.makedirs(output_folder, exist_ok=True)
            audio_segment.process_audio(output_folder=output_folder, i=i)
        else:
            print(f"Skipping non-audio file: {filename}")

if __name__ == "__main__":
    process_all_audio_files(AUDIO_FOLDER)
