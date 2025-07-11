import struct

# Read the file
with open('recordings/1.wav', 'rb') as f:
    data = f.read()

# Calculate correct sizes
file_size = len(data)
actual_data_size = file_size - 44  # Audio data size
riff_chunk_size = file_size - 8    # RIFF chunk size

# Fix the header
header = bytearray(data[:44])
header[4:8] = struct.pack('<I', riff_chunk_size)    # Fix RIFF chunk size
header[40:44] = struct.pack('<I', actual_data_size)  # Fix data chunk size

# Write the fixed file
with open('recordings/1_fixed.wav', 'wb') as f:
    f.write(header)
    f.write(data[44:])

print("Fixed file saved as: recordings/1_fixed.wav")

# Test the fix
from pydub import AudioSegment
audio = AudioSegment.from_wav('recordings/1_fixed.wav')
print(f"Duration: {len(audio)} ms ({len(audio)/1000:.2f} seconds)")