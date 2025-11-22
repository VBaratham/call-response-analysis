"""Pitch estimation service - extracts pitch contours for entire track."""
import json
import sys
from pathlib import Path
from typing import List, Optional
import numpy as np
import librosa


def log(message: str):
    """Print and flush immediately."""
    print(message)
    sys.stdout.flush()


def progress_bar(percent, width=30):
    """Create a simple text progress bar."""
    filled = int(width * percent / 100)
    bar = '=' * filled + '-' * (width - filled)
    return f"[{bar}] {percent:3d}%"


class PitchEstimatorService:
    """Service for extracting pitch contours from audio."""

    def __init__(self, hop_length: int = 512, fmin: float = 80, fmax: float = 500):
        self.hop_length = hop_length
        self.fmin = fmin
        self.fmax = fmax

    def hz_to_semitones(self, f0: float, reference: float = 440.0) -> Optional[float]:
        """Convert frequency in Hz to semitones relative to reference (A4=440Hz)."""
        if f0 is None or np.isnan(f0) or f0 <= 0:
            return None
        return 12 * np.log2(f0 / reference)

    def extract_full_pitch(self, vocals_path: str, output_dir: Path) -> dict:
        """
        Extract pitch contour for the entire vocals track.

        Args:
            vocals_path: Path to vocals audio file
            output_dir: Directory to save pitch data

        Returns:
            Summary statistics
        """
        log("Pitch Estimation")
        log(progress_bar(0))

        log("Loading vocals...")
        y, sr = librosa.load(vocals_path, sr=None, mono=True)
        duration = len(y) / sr
        log(f"Duration: {duration/60:.1f} min")
        log(progress_bar(5))

        log("Extracting pitch contour...")

        # Process in chunks to show progress
        chunk_duration = 30  # seconds per chunk
        chunk_samples = int(chunk_duration * sr)
        n_chunks = max(1, len(y) // chunk_samples + (1 if len(y) % chunk_samples else 0))

        all_f0 = []
        all_voiced = []
        all_prob = []

        for i in range(n_chunks):
            start = i * chunk_samples
            end = min((i + 1) * chunk_samples, len(y))
            chunk = y[start:end]

            f0_chunk, voiced_chunk, prob_chunk = librosa.pyin(
                chunk, fmin=self.fmin, fmax=self.fmax, sr=sr,
                frame_length=2048, hop_length=self.hop_length
            )

            all_f0.append(f0_chunk)
            all_voiced.append(voiced_chunk)
            all_prob.append(prob_chunk)

            # Progress from 10% to 85%
            pct = 10 + int(75 * (i + 1) / n_chunks)
            log(progress_bar(pct))

        # Concatenate results
        f0 = np.concatenate(all_f0)
        voiced_flag = np.concatenate(all_voiced)
        voiced_prob = np.concatenate(all_prob)

        # Convert to time
        times = librosa.times_like(f0, sr=sr, hop_length=self.hop_length)

        voiced_count = np.sum(voiced_flag)
        log(f"Extracted {len(times)} frames, {voiced_count} voiced")

        # Build pitch data structure
        pitch_data = []
        for i, (t, freq, voiced, prob) in enumerate(zip(times, f0, voiced_flag, voiced_prob)):
            semitones = self.hz_to_semitones(freq) if voiced else None

            pitch_data.append({
                'time': float(t),
                'f0_hz': float(freq) if not np.isnan(freq) else None,
                'semitones': float(semitones) if semitones is not None else None,
                'voiced': bool(voiced),
                'voiced_prob': float(prob) if not np.isnan(prob) else 0.0
            })

        # Save full pitch data
        log(progress_bar(90))
        output_dir = Path(output_dir)
        pitch_path = output_dir / "pitch_full.json"
        with open(pitch_path, 'w') as f:
            json.dump({
                'duration': duration,
                'sample_rate': sr,
                'hop_length': self.hop_length,
                'frame_count': len(pitch_data),
                'pitch': pitch_data
            }, f)

        log(progress_bar(100))
        log("Pitch estimation complete")

        return {
            'duration': duration,
            'frame_count': len(pitch_data),
            'voiced_ratio': float(voiced_count / len(times))
        }

    def estimate_pitch(self, vocals_path: str, sections: List[dict],
                      output_dir: Path) -> dict:
        """
        Estimate pitch for all sections and save results.

        Args:
            vocals_path: Path to vocals audio file
            sections: List of section dicts with start, end, label
            output_dir: Directory to save pitch data

        Returns:
            Summary statistics
        """
        log("Pair Pitch Estimation")
        log(progress_bar(0))

        y, sr = librosa.load(vocals_path, sr=None, mono=True)
        log(f"Duration: {len(y)/sr/60:.1f} min")

        output_dir = Path(output_dir)

        # Separate calls and responses
        calls = [s for s in sections if s['label'] == 'call']
        responses = [s for s in sections if s['label'] == 'response']

        # Match pairs
        n_pairs = min(len(calls), len(responses))
        log(f"Processing {n_pairs} pairs...")
        log(progress_bar(5))

        alignments = []

        for i in range(n_pairs):
            call = calls[i]
            response = responses[i]

            # Extract call pitch
            call_start = int(call['start'] * sr)
            call_end = int(call['end'] * sr)
            call_audio = y[call_start:call_end]
            call_pitch = self.extract_pitch_contour(call_audio, sr, call['start'])

            # Extract response pitch
            resp_start = int(response['start'] * sr)
            resp_end = int(response['end'] * sr)
            resp_audio = y[resp_start:resp_end]
            response_pitch = self.extract_pitch_contour(resp_audio, sr, response['start'])

            # Save pitch data
            call_path = output_dir / f"pitch_call_{i}.json"
            response_path = output_dir / f"pitch_response_{i}.json"

            with open(call_path, 'w') as f:
                json.dump(call_pitch, f)
            with open(response_path, 'w') as f:
                json.dump(response_pitch, f)

            # Calculate optimal alignment
            optimal_offset, correlation = self.find_optimal_offset(call_pitch, response_pitch)

            alignments.append({
                'pair_id': i,
                'call_section_id': call['id'],
                'response_section_id': response['id'],
                'optimal_offset': float(optimal_offset),
                'correlation': float(correlation) if correlation is not None else None,
                'custom_offset': None
            })

            # Progress from 10% to 90%
            pct = 10 + int(80 * (i + 1) / n_pairs)
            log(progress_bar(pct))

        # Save alignments
        alignments_path = output_dir / "alignments.json"
        with open(alignments_path, 'w') as f:
            json.dump(alignments, f, indent=2)

        log(progress_bar(100))
        log(f"Processed {n_pairs} pairs")

        return {
            'pairs_processed': n_pairs,
            'alignments': alignments
        }

    def find_optimal_offset(self, call_pitch: List[dict],
                           response_pitch: List[dict],
                           search_range: float = 2.0,
                           step: float = 0.01) -> tuple:
        """
        Find optimal time offset between call and response pitch contours.

        Args:
            call_pitch: Call pitch contour
            response_pitch: Response pitch contour
            search_range: Search range in seconds (-range to +range)
            step: Step size in seconds

        Returns:
            (optimal_offset, correlation)
        """
        # Extract voiced semitone values
        call_data = [(p['relative_time'], p['semitones'])
                     for p in call_pitch if p['semitones'] is not None]
        response_data = [(p['relative_time'], p['semitones'])
                        for p in response_pitch if p['semitones'] is not None]

        if len(call_data) < 10 or len(response_data) < 10:
            return 0.0, None

        call_times = np.array([d[0] for d in call_data])
        call_semitones = np.array([d[1] for d in call_data])
        response_times = np.array([d[0] for d in response_data])
        response_semitones = np.array([d[1] for d in response_data])

        best_offset = 0.0
        best_correlation = -1.0

        # Search for optimal offset
        offsets = np.arange(-search_range, search_range + step, step)

        for offset in offsets:
            correlation = self._compute_correlation_at_offset(
                call_times, call_semitones,
                response_times, response_semitones,
                offset
            )

            if correlation is not None and correlation > best_correlation:
                best_correlation = correlation
                best_offset = offset

        return best_offset, best_correlation if best_correlation > -1 else None

    def _compute_correlation_at_offset(self, call_times: np.ndarray,
                                       call_semitones: np.ndarray,
                                       response_times: np.ndarray,
                                       response_semitones: np.ndarray,
                                       offset: float) -> Optional[float]:
        """Compute correlation between pitch contours at given offset."""
        # Shift response times
        shifted_response_times = response_times + offset

        # Find overlapping range
        overlap_start = max(call_times.min(), shifted_response_times.min())
        overlap_end = min(call_times.max(), shifted_response_times.max())

        if overlap_start >= overlap_end:
            return None

        # Interpolate to common time grid
        n_points = min(100, int((overlap_end - overlap_start) * 50))
        if n_points < 10:
            return None

        common_times = np.linspace(overlap_start, overlap_end, n_points)

        try:
            call_interp = np.interp(common_times, call_times, call_semitones)
            response_interp = np.interp(common_times, shifted_response_times, response_semitones)

            # Compute Pearson correlation
            correlation = np.corrcoef(call_interp, response_interp)[0, 1]

            return float(correlation) if not np.isnan(correlation) else None
        except Exception:
            return None

    def get_pitch_stats(self, pitch_contour: List[dict]) -> dict:
        """Compute statistics for a pitch contour."""
        voiced_points = [p for p in pitch_contour if p['semitones'] is not None]

        if not voiced_points:
            return {
                'mean_pitch': None,
                'pitch_range': None,
                'pitch_std': None,
                'voiced_ratio': 0.0
            }

        semitones = [p['semitones'] for p in voiced_points]
        f0_values = [p['f0_hz'] for p in voiced_points if p['f0_hz'] is not None]

        return {
            'mean_pitch_hz': float(np.mean(f0_values)) if f0_values else None,
            'mean_semitones': float(np.mean(semitones)),
            'pitch_range': float(max(semitones) - min(semitones)),
            'pitch_std': float(np.std(semitones)),
            'voiced_ratio': len(voiced_points) / len(pitch_contour)
        }
