#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Audio Engine for Tonic Solfa Studio
Generates WAV and MP3 files from music scores using synthesis and MIDI.
Supports various instruments and quality settings.
"""

import io
import struct
import math
from dataclasses import dataclass
from typing import List, Optional, Tuple
from enum import Enum

# Color palette for UI
DARK   = "#1a1a2e"
PANEL  = "#16213e"
CARD   = "#0f3460"
ACCENT = "#e94560"
GOLD   = "#f5a623"
TEXT   = "#eaeaea"
MUTED  = "#8892a4"
GREEN  = "#00d4aa"
WHITE  = "#ffffff"


class Instrument(Enum):
    """Available instruments for synthesis."""
    SINE = "sine"           # Pure sine wave
    TRIANGLE = "triangle"   # Triangle wave
    SQUARE = "square"       # Square wave
    SAWTOOTH = "sawtooth"   # Sawtooth wave
    PIANO = "piano"         # Piano (synthetic)
    BELL = "bell"           # Bell/chime
    FLUTE = "flute"         # Flute


class WavFormat(Enum):
    """WAV file formats."""
    MONO_16BIT_44K = (1, 16, 44100)
    MONO_16BIT_48K = (1, 16, 48000)
    STEREO_16BIT_44K = (2, 16, 44100)
    STEREO_16BIT_48K = (2, 16, 48000)


@dataclass
class AudioConfig:
    """Audio generation configuration."""
    sample_rate: int = 44100      # Samples per second
    bit_depth: int = 16            # 8, 16, or 24
    num_channels: int = 1          # 1 (mono) or 2 (stereo)
    instrument: Instrument = Instrument.SINE
    tempo_bpm: int = 120
    volume: float = 0.7            # 0.0 to 1.0
    envelope: str = "simple"       # simple, adsr, percussive


class WaveformGenerator:
    """Generates audio waveforms."""
    
    @staticmethod
    def sine(frequency: float, duration: float, sample_rate: int,
             phase: float = 0.0) -> List[float]:
        """Generate sine wave."""
        num_samples = int(duration * sample_rate)
        samples = []
        for i in range(num_samples):
            t = i / sample_rate
            value = math.sin(2 * math.pi * frequency * t + phase)
            samples.append(value)
        return samples
    
    @staticmethod
    def triangle(frequency: float, duration: float, sample_rate: int) -> List[float]:
        """Generate triangle wave."""
        num_samples = int(duration * sample_rate)
        period = sample_rate / frequency
        samples = []
        for i in range(num_samples):
            # Sawtooth from 0 to 2pi
            phase = (2 * math.pi * i / period) % (2 * math.pi)
            # Convert to triangle
            if phase < math.pi:
                value = (phase / math.pi) * 2 - 1
            else:
                value = 2 - (phase / math.pi) * 2
            samples.append(value)
        return samples
    
    @staticmethod
    def square(frequency: float, duration: float, sample_rate: int) -> List[float]:
        """Generate square wave."""
        num_samples = int(duration * sample_rate)
        period = sample_rate / frequency
        samples = []
        for i in range(num_samples):
            phase = (i % int(period)) / period
            value = 1.0 if phase < 0.5 else -1.0
            samples.append(value)
        return samples
    
    @staticmethod
    def sawtooth(frequency: float, duration: float, sample_rate: int) -> List[float]:
        """Generate sawtooth wave."""
        num_samples = int(duration * sample_rate)
        period = sample_rate / frequency
        samples = []
        for i in range(num_samples):
            phase = (i % int(period)) / period
            value = 2 * phase - 1
            samples.append(value)
        return samples
    
    @staticmethod
    def piano(frequency: float, duration: float, sample_rate: int) -> List[float]:
        """Generate piano-like sound with decay."""
        base = WaveformGenerator.triangle(frequency, duration, sample_rate)
        # Add some harmonics
        second = WaveformGenerator.sine(frequency * 2, duration, sample_rate)
        third = WaveformGenerator.sine(frequency * 3, duration, sample_rate)
        
        samples = []
        for i, (b, s, t) in enumerate(zip(base, second, third)):
            # Exponential decay
            decay = math.exp(-3 * i / (sample_rate * duration))
            val = (b * 0.6 + s * 0.2 + t * 0.1) * decay
            samples.append(val)
        return samples
    
    @staticmethod
    def bell(frequency: float, duration: float, sample_rate: int) -> List[float]:
        """Generate bell-like sound."""
        # Multiple frequencies for rich timbre
        f1 = frequency
        f2 = frequency * 1.5
        f3 = frequency * 2.3
        
        s1 = WaveformGenerator.sine(f1, duration, sample_rate)
        s2 = WaveformGenerator.sine(f2, duration, sample_rate)
        s3 = WaveformGenerator.sine(f3, duration, sample_rate)
        
        samples = []
        for i, (a, b, c) in enumerate(zip(s1, s2, s3)):
            # Exponential decay with longer tail
            decay = math.exp(-1.5 * i / (sample_rate * duration))
            val = (a * 0.5 + b * 0.3 + c * 0.2) * decay
            samples.append(val)
        return samples
    
    @staticmethod
    def flute(frequency: float, duration: float, sample_rate: int) -> List[float]:
        """Generate flute-like sound."""
        base = WaveformGenerator.sine(frequency, duration, sample_rate)
        harmonic = WaveformGenerator.sine(frequency * 2, duration, sample_rate)
        
        samples = []
        for i, (b, h) in enumerate(zip(base, harmonic)):
            # Flute has softer attack
            attack = min(1.0, i / (0.05 * sample_rate))
            decay = math.exp(-1.0 * i / (sample_rate * duration))
            val = (b * 0.8 + h * 0.2) * attack * decay
            samples.append(val)
        return samples


class EnvelopeGenerator:
    """Generates amplitude envelopes (ADSR)."""
    
    @staticmethod
    def simple(duration: float, sample_rate: int) -> List[float]:
        """Simple attack-release envelope."""
        num_samples = int(duration * sample_rate)
        attack_samples = int(0.01 * sample_rate)  # 10ms attack
        release_samples = int(0.1 * sample_rate)  # 100ms release
        sustain_duration = duration - 0.01 - 0.1
        
        envelope = []
        
        # Attack
        for i in range(min(attack_samples, num_samples)):
            envelope.append(i / attack_samples)
        
        # Sustain
        sustain_samples = int(sustain_duration * sample_rate)
        for i in range(sustain_samples):
            envelope.append(1.0)
        
        # Release
        for i in range(release_samples):
            envelope.append(1.0 - i / release_samples)
        
        # Pad to exact length
        while len(envelope) < num_samples:
            envelope.append(0.0)
        
        return envelope[:num_samples]
    
    @staticmethod
    def percussive(duration: float, sample_rate: int) -> List[float]:
        """Percussive envelope (fast attack, constant decay)."""
        num_samples = int(duration * sample_rate)
        attack_samples = int(0.005 * sample_rate)  # 5ms attack
        
        envelope = []
        
        # Quick attack
        for i in range(min(attack_samples, num_samples)):
            envelope.append(i / attack_samples)
        
        # Decay
        remaining = num_samples - len(envelope)
        for i in range(remaining):
            decay_factor = (remaining - i) / remaining
            envelope.append(decay_factor)
        
        return envelope[:num_samples]


class AudioSynthesizer:
    """Synthesizes audio from MIDI-like note data."""
    
    def __init__(self, config: AudioConfig):
        self.config = config
    
    def note_to_frequency(self, midi_note: int) -> float:
        """Convert MIDI note number to frequency (Hz)."""
        return 440.0 * (2.0 ** ((midi_note - 69) / 12.0))
    
    def generate_note(self, midi_note: int, duration: float, velocity: int = 100) -> List[float]:
        """Generate audio for a single note."""
        frequency = self.note_to_frequency(midi_note)
        
        # Generate waveform
        if self.config.instrument == Instrument.SINE:
            samples = WaveformGenerator.sine(frequency, duration, self.config.sample_rate)
        elif self.config.instrument == Instrument.TRIANGLE:
            samples = WaveformGenerator.triangle(frequency, duration, self.config.sample_rate)
        elif self.config.instrument == Instrument.SQUARE:
            samples = WaveformGenerator.square(frequency, duration, self.config.sample_rate)
        elif self.config.instrument == Instrument.SAWTOOTH:
            samples = WaveformGenerator.sawtooth(frequency, duration, self.config.sample_rate)
        elif self.config.instrument == Instrument.PIANO:
            samples = WaveformGenerator.piano(frequency, duration, self.config.sample_rate)
        elif self.config.instrument == Instrument.BELL:
            samples = WaveformGenerator.bell(frequency, duration, self.config.sample_rate)
        elif self.config.instrument == Instrument.FLUTE:
            samples = WaveformGenerator.flute(frequency, duration, self.config.sample_rate)
        else:
            samples = WaveformGenerator.sine(frequency, duration, self.config.sample_rate)
        
        # Generate envelope
        if self.config.envelope == "adsr" or self.config.envelope == "simple":
            envelope = EnvelopeGenerator.simple(duration, self.config.sample_rate)
        elif self.config.envelope == "percussive":
            envelope = EnvelopeGenerator.percussive(duration, self.config.sample_rate)
        else:
            envelope = [1.0] * len(samples)
        
        # Apply envelope and volume
        velocity_factor = velocity / 100.0
        output = []
        for sample, env in zip(samples, envelope):
            output.append(sample * env * self.config.volume * velocity_factor)
        
        return output
    
    def generate_from_score(self, score) -> List[float]:
        """Generate audio from a Score object."""
        all_samples = []
        beat_duration = 60.0 / self.config.tempo_bpm
        
        for measure in score.measures:
            for note in measure.notes:
                duration = note.beats * beat_duration
                
                if note.rest:
                    # Silence
                    silence = [0.0] * int(duration * self.config.sample_rate)
                    all_samples.extend(silence)
                else:
                    # Generate note
                    note_samples = self.generate_note(note.midi_num, duration, 80)
                    all_samples.extend(note_samples)
        
        return all_samples


class WavFileWriter:
    """Writes WAV files."""
    
    @staticmethod
    def write_wav(filename: str, samples: List[float], config: AudioConfig):
        """Write samples to WAV file."""
        # Normalize samples to prevent clipping
        max_sample = max(abs(s) for s in samples) if samples else 1.0
        if max_sample > 1.0:
            samples = [s / max_sample for s in samples]
        
        # Convert to integer samples
        max_int = (2 ** (config.bit_depth - 1)) - 1
        int_samples = [int(s * max_int) for s in samples]
        
        # Build WAV file structure
        num_channels = config.num_channels
        sample_rate = config.sample_rate
        bit_depth = config.bit_depth
        byte_rate = sample_rate * num_channels * bit_depth // 8
        block_align = num_channels * bit_depth // 8
        
        # WAV header
        wav_data = io.BytesIO()
        
        # RIFF header
        wav_data.write(b'RIFF')
        # File size (placeholder, will update)
        file_size_pos = wav_data.tell()
        wav_data.write(struct.pack('<I', 36 + len(int_samples) * 2))
        wav_data.write(b'WAVE')
        
        # fmt subchunk
        wav_data.write(b'fmt ')
        wav_data.write(struct.pack('<I', 16))  # Subchunk1Size
        wav_data.write(struct.pack('<H', 1))   # AudioFormat (PCM)
        wav_data.write(struct.pack('<H', num_channels))
        wav_data.write(struct.pack('<I', sample_rate))
        wav_data.write(struct.pack('<I', byte_rate))
        wav_data.write(struct.pack('<H', block_align))
        wav_data.write(struct.pack('<H', bit_depth))
        
        # data subchunk
        wav_data.write(b'data')
        wav_data.write(struct.pack('<I', len(int_samples) * 2))
        
        # Write audio data (16-bit little-endian)
        for sample in int_samples:
            wav_data.write(struct.pack('<h', sample))
        
        # Update file size
        file_size = wav_data.tell() - 8
        wav_data.seek(file_size_pos)
        wav_data.write(struct.pack('<I', file_size))
        
        # Write to file
        with open(filename, 'wb') as f:
            f.write(wav_data.getvalue())
    
    @staticmethod
    def write_wav_bytes(samples: List[float], config: AudioConfig) -> bytes:
        """Generate WAV file as bytes."""
        max_sample = max(abs(s) for s in samples) if samples else 1.0
        if max_sample > 1.0:
            samples = [s / max_sample for s in samples]
        
        max_int = (2 ** (config.bit_depth - 1)) - 1
        int_samples = [int(s * max_int) for s in samples]
        
        num_channels = config.num_channels
        sample_rate = config.sample_rate
        bit_depth = config.bit_depth
        byte_rate = sample_rate * num_channels * bit_depth // 8
        block_align = num_channels * bit_depth // 8
        
        wav_data = io.BytesIO()
        
        wav_data.write(b'RIFF')
        file_size_pos = wav_data.tell()
        wav_data.write(struct.pack('<I', 36 + len(int_samples) * 2))
        wav_data.write(b'WAVE')
        
        wav_data.write(b'fmt ')
        wav_data.write(struct.pack('<I', 16))
        wav_data.write(struct.pack('<H', 1))
        wav_data.write(struct.pack('<H', num_channels))
        wav_data.write(struct.pack('<I', sample_rate))
        wav_data.write(struct.pack('<I', byte_rate))
        wav_data.write(struct.pack('<H', block_align))
        wav_data.write(struct.pack('<H', bit_depth))
        
        wav_data.write(b'data')
        wav_data.write(struct.pack('<I', len(int_samples) * 2))
        
        for sample in int_samples:
            wav_data.write(struct.pack('<h', sample))
        
        file_size = wav_data.tell() - 8
        wav_data.seek(file_size_pos)
        wav_data.write(struct.pack('<I', file_size))
        
        return wav_data.getvalue()


def export_score_to_wav(score, filename: str, 
                        instrument: Instrument = Instrument.PIANO,
                        sample_rate: int = 44100):
    """Export a Score to WAV file."""
    config = AudioConfig(
        sample_rate=sample_rate,
        instrument=instrument,
        tempo_bpm=score.tempo_bpm
    )
    
    synthesizer = AudioSynthesizer(config)
    samples = synthesizer.generate_from_score(score)
    WavFileWriter.write_wav(filename, samples, config)


# Example usage
if __name__ == '__main__':
    # Test the audio engine
    config = AudioConfig(instrument=Instrument.SINE)
    synth = AudioSynthesizer(config)
    
    # Generate a simple melody (C major scale)
    midi_notes = [60, 62, 64, 65, 67, 69, 71, 72]  # C D E F G A B C
    samples = []
    
    for midi_note in midi_notes:
        note_samples = synth.generate_note(midi_note, 0.5)  # 0.5 second per note
        samples.extend(note_samples)
    
    # Save to file
    WavFileWriter.write_wav('/tmp/test_scale.wav', samples, config)
    print("Generated test_scale.wav")
