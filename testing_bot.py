import os
import struct
import numpy as np
from pydub import AudioSegment

def diagnose_wav_file(filepath):
    """Comprehensive WAV file diagnostic tool"""
    
    print(f"=== Diagnosing: {filepath} ===\n")
    
    # 1. Basic file info
    if not os.path.exists(filepath):
        print("❌ File does not exist!")
        return
    
    file_size = os.path.getsize(filepath)
    print(f"📁 File size: {file_size:,} bytes ({file_size/1024/1024:.2f} MB)")
    
    # 2. Read and analyze WAV header
    try:
        with open(filepath, 'rb') as f:
            header = f.read(44)
            
        if len(header) < 44:
            print("❌ File too small to contain WAV header")
            return
            
        # Parse WAV header
        chunk_id = header[0:4]
        chunk_size = struct.unpack('<I', header[4:8])[0]
        format_type = header[8:12]
        subchunk1_id = header[12:16]
        subchunk1_size = struct.unpack('<I', header[16:20])[0]
        audio_format = struct.unpack('<H', header[20:22])[0]
        num_channels = struct.unpack('<H', header[22:24])[0]
        sample_rate = struct.unpack('<I', header[24:28])[0]
        byte_rate = struct.unpack('<I', header[28:32])[0]
        block_align = struct.unpack('<H', header[32:34])[0]
        bits_per_sample = struct.unpack('<H', header[34:36])[0]
        subchunk2_id = header[36:40]
        subchunk2_size = struct.unpack('<I', header[40:44])[0]
        
        print("📋 WAV Header Analysis:")
        print(f"   Chunk ID: {chunk_id} (should be b'RIFF')")
        print(f"   Format: {format_type} (should be b'WAVE')")
        print(f"   Audio Format: {audio_format} (1=PCM)")
        print(f"   Channels: {num_channels}")
        print(f"   Sample Rate: {sample_rate:,} Hz")
        print(f"   Bits per Sample: {bits_per_sample}")
        print(f"   Data Size: {subchunk2_size:,} bytes")
        
        # Validate header
        valid_header = True
        if chunk_id != b'RIFF':
            print("❌ Invalid RIFF header")
            valid_header = False
        if format_type != b'WAVE':
            print("❌ Invalid WAVE format")
            valid_header = False
        if audio_format != 1:
            print(f"⚠️  Non-PCM format (format={audio_format})")
            
        if valid_header:
            print("✅ WAV header appears valid")
            
        # Calculate expected duration
        if sample_rate > 0 and num_channels > 0 and bits_per_sample > 0:
            bytes_per_second = sample_rate * num_channels * (bits_per_sample // 8)
            expected_duration_ms = (subchunk2_size / bytes_per_second) * 1000
            print(f"📊 Expected duration: {expected_duration_ms:.2f} ms ({expected_duration_ms/1000:.2f} seconds)")
        else:
            print("❌ Invalid audio parameters in header")
            
    except Exception as e:
        print(f"❌ Error reading WAV header: {e}")
        return
    
    # 3. Try pydub loading
    print("\n🎵 Pydub Analysis:")
    try:
        audio = AudioSegment.from_wav(filepath)
        print(f"   Duration: {len(audio)} ms")
        print(f"   Frame rate: {audio.frame_rate} Hz")
        print(f"   Channels: {audio.channels}")
        print(f"   Sample width: {audio.sample_width} bytes")
        print(f"   Max amplitude: {audio.max}")
        
        if len(audio) == 0:
            print("❌ Pydub reports 0ms duration")
        else:
            print("✅ Pydub loaded successfully")
            
    except Exception as e:
        print(f"❌ Pydub loading failed: {e}")
    
    # 4. Analyze actual audio data
    print("\n🔍 Raw Audio Data Analysis:")
    try:
        with open(filepath, 'rb') as f:
            # Skip header (typically 44 bytes, but let's be more careful)
            f.seek(44)
            raw_data = f.read()
            
        if len(raw_data) == 0:
            print("❌ No audio data after header")
            return
            
        print(f"   Raw data size: {len(raw_data):,} bytes")
        
        # Convert to numpy array (assuming 16-bit stereo)
        if bits_per_sample == 16 and num_channels == 2:
            # Interpret as 16-bit signed integers
            audio_array = np.frombuffer(raw_data, dtype=np.int16)
            print(f"   Audio samples: {len(audio_array):,}")
            print(f"   Min value: {audio_array.min()}")
            print(f"   Max value: {audio_array.max()}")
            print(f"   Mean: {audio_array.mean():.2f}")
            print(f"   Std deviation: {audio_array.std():.2f}")
            
            # Check for silence
            non_zero_samples = np.count_nonzero(audio_array)
            print(f"   Non-zero samples: {non_zero_samples:,} ({non_zero_samples/len(audio_array)*100:.2f}%)")
            
            if non_zero_samples == 0:
                print("❌ ALL SAMPLES ARE ZERO - FILE CONTAINS ONLY SILENCE!")
            elif non_zero_samples < len(audio_array) * 0.01:  # Less than 1% non-zero
                print("⚠️  File contains mostly silence")
            else:
                print("✅ File contains audio data")
                
            # Show first few samples
            print(f"   First 10 samples: {audio_array[:10]}")
            
    except Exception as e:
        print(f"❌ Error analyzing raw audio data: {e}")
    
    # 5. Alternative loading attempts
    print("\n🔧 Alternative Loading Attempts:")
    
    # Try librosa
    try:
        import librosa
        y, sr = librosa.load(filepath, sr=None)
        duration_ms = len(y) / sr * 1000
        print(f"   Librosa: {duration_ms:.2f} ms, max amplitude: {np.max(np.abs(y)):.6f}")
        if duration_ms > 0:
            print("✅ Librosa loaded successfully")
    except ImportError:
        print("   Librosa not available (pip install librosa)")
    except Exception as e:
        print(f"   Librosa failed: {e}")
    
    # Try raw loading with pydub
    try:
        audio_raw = AudioSegment.from_raw(
            filepath, 
            frame_rate=sample_rate,
            channels=num_channels,
            sample_width=bits_per_sample//8
        )
        print(f"   Raw pydub: {len(audio_raw)} ms")
        if len(audio_raw) > 0:
            print("✅ Raw pydub loading worked!")
    except Exception as e:
        print(f"   Raw pydub failed: {e}")

# Usage
filepath = 'recordings/1.wav'
diagnose_wav_file(filepath)

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
import os
import struct
from pydub import AudioSegment

def fix_wav_header(input_filepath, output_filepath=None):
    """
    Fix a WAV file with corrupted header by completely rebuilding it
    """
    if output_filepath is None:
        output_filepath = input_filepath.replace('.wav', '_fixed.wav')
    
    print(f"🔧 Fixing WAV header: {input_filepath} -> {output_filepath}")
    
    # Read the entire file
    with open(input_filepath, 'rb') as f:
        data = f.read()
    
    # Get file size
    file_size = len(data)
    print(f"📁 Total file size: {file_size:,} bytes")
    
    # Parse original header to get audio parameters
    with open(input_filepath, 'rb') as f:
        header = f.read(44)
    
    num_channels = struct.unpack('<H', header[22:24])[0]
    sample_rate = struct.unpack('<I', header[24:28])[0]
    bits_per_sample = struct.unpack('<H', header[34:36])[0]
    
    print(f"📊 Audio parameters: {sample_rate}Hz, {num_channels} channels, {bits_per_sample}-bit")
    
    # Find the actual start of audio data by looking for "data" chunk
    audio_data_start = 44  # Default assumption
    audio_data = data[44:]  # Default audio data
    
    # Look for "data" chunk in case header is non-standard
    for i in range(12, len(data) - 8):
        if data[i:i+4] == b'data':
            chunk_size = struct.unpack('<I', data[i+4:i+8])[0]
            print(f"Found 'data' chunk at offset {i}, size: {chunk_size}")
            if chunk_size > 0:
                audio_data_start = i + 8
                audio_data = data[audio_data_start:audio_data_start + chunk_size]
                break
    
    # If no valid data chunk found, use everything after byte 44
    if audio_data_start == 44:
        audio_data = data[44:]
        print(f"Using default: audio data from byte 44, size: {len(audio_data)}")
    
    actual_data_size = len(audio_data)
    print(f"📊 Actual audio data size: {actual_data_size:,} bytes")
    
    # Calculate duration
    bytes_per_second = sample_rate * num_channels * (bits_per_sample // 8)
    duration_seconds = actual_data_size / bytes_per_second
    print(f"📊 Expected duration: {duration_seconds:.2f} seconds")
    
    # Build a completely new WAV header
    new_header = bytearray()
    
    # RIFF header
    new_header.extend(b'RIFF')
    new_header.extend(struct.pack('<I', 36 + actual_data_size))  # File size - 8
    new_header.extend(b'WAVE')
    
    # Format chunk
    new_header.extend(b'fmt ')
    new_header.extend(struct.pack('<I', 16))  # Format chunk size
    new_header.extend(struct.pack('<H', 1))   # PCM format
    new_header.extend(struct.pack('<H', num_channels))
    new_header.extend(struct.pack('<I', sample_rate))
    new_header.extend(struct.pack('<I', bytes_per_second))  # Byte rate
    new_header.extend(struct.pack('<H', num_channels * (bits_per_sample // 8)))  # Block align
    new_header.extend(struct.pack('<H', bits_per_sample))
    
    # Data chunk
    new_header.extend(b'data')
    new_header.extend(struct.pack('<I', actual_data_size))
    
    print(f"📋 New header size: {len(new_header)} bytes")
    
    # Write the completely reconstructed file
    with open(output_filepath, 'wb') as f:
        f.write(new_header)
        f.write(audio_data)
    
    print(f"✅ Rebuilt WAV file saved as: {output_filepath}")
    
    # Verify the fix
    print("\n🔍 Verifying fixed file:")
    try:
        audio = AudioSegment.from_wav(output_filepath)
        duration_ms = len(audio)
        duration_seconds = duration_ms / 1000
        
        print(f"   Duration: {duration_ms:,} ms ({duration_seconds:.2f} seconds)")
        print(f"   Frame rate: {audio.frame_rate} Hz")
        print(f"   Channels: {audio.channels}")
        print(f"   Sample width: {audio.sample_width} bytes")
        print(f"   Max amplitude: {audio.max}")
        
        if duration_ms > 0:
            print("✅ SUCCESS: Fixed file loads correctly!")
            return output_filepath
        else:
            print("❌ Fix failed - still 0ms duration")
            return None
            
    except Exception as e:
        print(f"❌ Error verifying fixed file: {e}")
        return None

def batch_fix_wav_files(recordings_dir='recordings'):
    """
    Fix all WAV files in a directory
    """
    print(f"🔧 Batch fixing WAV files in: {recordings_dir}")
    
    if not os.path.exists(recordings_dir):
        print(f"❌ Directory {recordings_dir} does not exist")
        return
    
    fixed_files = []
    
    for filename in os.listdir(recordings_dir):
        if filename.endswith('.wav') and not filename.endswith('_fixed.wav'):
            filepath = os.path.join(recordings_dir, filename)
            print(f"\n--- Processing: {filename} ---")
            
            # Check if file needs fixing
            try:
                audio = AudioSegment.from_wav(filepath)
                if len(audio) == 0:
                    print("❌ File has 0ms duration - needs fixing")
                    output_path = fix_wav_header(filepath)
                    if output_path:
                        fixed_files.append(output_path)
                else:
                    print("✅ File already works correctly")
            except Exception as e:
                print(f"❌ Error checking file: {e}")
    
    print(f"\n📋 Summary: Fixed {len(fixed_files)} files")
    for filepath in fixed_files:
        print(f"   ✅ {filepath}")
    
    return fixed_files

# Fix your specific file
input_file = 'recordings/2.wav'
fixed_file = fix_wav_header(input_file)

# Or fix all files in the recordings directory
# fixed_files = batch_fix_wav_files('recordings')