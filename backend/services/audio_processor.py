"""Audio processing service - handles vocal separation using Demucs."""
import ssl
import os
import sys
from pathlib import Path
import numpy as np
import torch
import soundfile as sf

# Fix SSL certificate verification for downloading models
ssl._create_default_https_context = ssl._create_unverified_context


def simple_progress_bar(percent, width=30):
    """Create a simple text progress bar."""
    filled = int(width * percent / 100)
    bar = '=' * filled + '-' * (width - filled)
    return f"[{bar}] {percent:3d}%"


class AudioProcessorService:
    """Service for audio processing operations."""

    def __init__(self):
        self._model = None
        self._model_sr = None

    def _load_model(self):
        """Lazy-load the Demucs model."""
        if self._model is None:
            from demucs.pretrained import get_model
            print("Loading model...")
            self._model = get_model('htdemucs')
            self._model.eval()
            self._model_sr = self._model.samplerate
        return self._model

    def separate_vocals(self, input_path: str, output_dir: str) -> str:
        """
        Separate vocals from audio file using Demucs.

        Args:
            input_path: Path to input audio file
            output_dir: Directory to save output files

        Returns:
            Path to the separated vocals file
        """
        from pydub import AudioSegment
        from demucs.apply import apply_model

        print(f"Separating vocals from: {os.path.basename(input_path)}")

        # Load audio
        print(simple_progress_bar(5))
        audio = AudioSegment.from_file(input_path)
        duration_sec = len(audio) / 1000.0
        print(f"Duration: {duration_sec/60:.1f} min")

        # Convert to tensor
        print(simple_progress_bar(10))
        samples = np.array(audio.get_array_of_samples())
        if audio.channels == 2:
            samples = samples.reshape((-1, 2)).T
        else:
            samples = samples.reshape((1, -1))
        waveform = torch.FloatTensor(samples) / 32768.0
        sr = audio.frame_rate

        # Load model
        print(simple_progress_bar(15))
        model = self._load_model()

        # Resample if necessary
        if sr != self._model_sr:
            import torchaudio
            resampler = torchaudio.transforms.Resample(sr, self._model_sr)
            waveform = resampler(waveform)
            sr = self._model_sr

        # Ensure stereo
        if waveform.shape[0] == 1:
            waveform = waveform.repeat(2, 1)

        # Apply model (suppress tqdm output)
        print(simple_progress_bar(20))
        print("Running separation (this takes a while)...")

        import io
        from contextlib import redirect_stderr

        with torch.no_grad():
            # Suppress tqdm output by redirecting stderr
            try:
                with redirect_stderr(io.StringIO()):
                    sources = apply_model(
                        model,
                        waveform.unsqueeze(0),
                        device='cpu',
                        progress=False,
                        num_workers=0
                    )[0]
            except TypeError:
                with redirect_stderr(io.StringIO()):
                    sources = apply_model(model, waveform.unsqueeze(0), device='cpu')[0]

        print(simple_progress_bar(90))

        # Save vocals
        source_names = model.sources
        vocals_idx = source_names.index('vocals') if 'vocals' in source_names else 0

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        vocals_path = output_dir / "vocals.wav"
        vocals_np = sources[vocals_idx].cpu().numpy().T
        sf.write(str(vocals_path), vocals_np, sr)

        print(simple_progress_bar(100))
        print("Vocal separation complete!")

        return str(vocals_path)

    def get_audio_info(self, audio_path: str) -> dict:
        """Get basic information about an audio file."""
        info = sf.info(audio_path)
        return {
            "duration": info.duration,
            "sample_rate": info.samplerate,
            "channels": info.channels,
            "frames": info.frames
        }

    def extract_segment(self, audio_path: str, start: float, end: float) -> np.ndarray:
        """Extract a segment from an audio file."""
        import librosa
        y, sr = librosa.load(audio_path, sr=None, mono=False,
                            offset=start, duration=end - start)
        return y, sr
