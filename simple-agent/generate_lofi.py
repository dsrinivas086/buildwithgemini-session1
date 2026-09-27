import math
import numpy as np
import wave

SAMPLE_RATE = 44100
DURATION = 35.0  # seconds

def create_lofi_track():
    num_samples = int(SAMPLE_RATE * DURATION)
    audio = np.zeros((num_samples, 2), dtype=np.float32)
    
    bpm = 85
    beat_sec = 60.0 / bpm
    bar_sec = beat_sec * 4
    
    # 1. Chord Progression (Cmaj7 -> Am7 -> Dm7 -> G7)
    # Frequencies for warm lo-fi chords
    chords = [
        [261.63, 329.63, 392.00, 493.88],  # Cmaj7 (C4, E4, G4, B4)
        [220.00, 261.63, 329.63, 392.00],  # Am7   (A3, C4, E4, G4)
        [293.66, 349.23, 440.00, 523.25],  # Dm7   (D4, F4, A4, C5)
        [196.00, 246.94, 293.66, 349.23],  # G7    (G3, B3, D4, F4)
    ]
    
    t = np.linspace(0, DURATION, num_samples, endpoint=False)
    
    # Generate warm synth pads
    synth = np.zeros(num_samples, dtype=np.float32)
    for i, chord in enumerate(chords):
        start_t = i * bar_sec
        while start_t < DURATION:
            end_t = start_t + bar_sec
            mask = (t >= start_t) & (t < end_t)
            t_slice = t[mask] - start_t
            
            # Smooth envelope
            env = np.sin(np.pi * (t_slice / bar_sec)) ** 0.5
            
            for freq in chord:
                # Soft sine + subtle 2nd harmonic for warmth
                wave_harm = np.sin(2 * np.pi * freq * t_slice) * 0.6 + np.sin(2 * np.pi * freq * 2 * t_slice) * 0.15
                synth[mask] += wave_harm * env * 0.12
            
            start_t += len(chords) * bar_sec

    # Apply soft low-pass filter (moving average) for lo-fi chill sound
    window_size = 15
    synth = np.convolve(synth, np.ones(window_size)/window_size, mode='same')
    
    # 2. Drums (Upbeat Lo-Fi Beat: Kick, Snare, Hi-Hat)
    drums = np.zeros(num_samples, dtype=np.float32)
    step_sec = beat_sec / 4  # 16th notes
    
    total_steps = int(DURATION / step_sec)
    for step in range(total_steps):
        step_time = step * step_sec
        step_idx = int(step_time * SAMPLE_RATE)
        pattern_pos = step % 16
        
        # Kick drum (on 0, 7, 10)
        if pattern_pos in [0, 7, 10]:
            k_len = int(0.12 * SAMPLE_RATE)
            if step_idx + k_len < num_samples:
                kt = np.linspace(0, 0.12, k_len)
                # Pitch sweep 150Hz down to 40Hz
                freq_sweep = 40 + (150 - 40) * np.exp(-kt * 30)
                phase = 2 * np.pi * np.cumsum(freq_sweep) / SAMPLE_RATE
                k_env = np.exp(-kt * 20)
                drums[step_idx:step_idx+k_len] += np.sin(phase) * k_env * 0.45
                
        # Snare drum (on 4, 12)
        if pattern_pos in [4, 12]:
            s_len = int(0.15 * SAMPLE_RATE)
            if step_idx + s_len < num_samples:
                st = np.linspace(0, 0.15, s_len)
                noise = np.random.uniform(-1, 1, s_len)
                s_env = np.exp(-st * 25)
                drums[step_idx:step_idx+s_len] += noise * s_env * 0.25

        # Hi-hat (every 8th note, even steps)
        if pattern_pos % 2 == 0:
            h_len = int(0.04 * SAMPLE_RATE)
            if step_idx + h_len < num_samples:
                ht = np.linspace(0, 0.04, h_len)
                noise = np.random.uniform(-1, 1, h_len)
                h_env = np.exp(-ht * 60)
                drums[step_idx:step_idx+h_len] += noise * h_env * 0.08

    # 3. Add Vinyl Crackle / Warm Noise
    crackle = np.random.normal(0, 0.005, num_samples)
    
    # Combine audio channels (Stereo with subtle pan)
    left = synth * 0.95 + drums + crackle
    right = synth * 1.05 + drums + crackle
    
    audio[:, 0] = left
    audio[:, 1] = right
    
    # Normalize peak audio
    max_val = np.max(np.abs(audio))
    if max_val > 0:
        audio = audio / max_val * 0.85

    # Convert to 16-bit PCM WAV
    audio_int16 = (audio * 32767).astype(np.int16)
    
    with wave.open("lofi_music.wav", "w") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio_int16.tobytes())
        
    print("✅ Created lo-fi music track: lofi_music.wav")

if __name__ == "__main__":
    create_lofi_track()
