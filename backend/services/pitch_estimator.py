"""Pitch estimation service - extracts pitch contours for entire track."""
import json
from pathlib import Path
from typing import List, Optional
import numpy as np
import librosa


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
        import sys

        print(f"\n{'=' * 50}")
        print("PITCH ESTIMATION (FULL TRACK)")
        print(f"{'=' * 50}")

        print("\n[1/2] Loading vocals...")
        y, sr = librosa.load(vocals_path, sr=None, mono=True)
        duration = len(y) / sr
        print(f"  Duration: {duration:.1f} seconds")
        print(f"  Sample rate: {sr}Hz")

        print("\n[2/2] Extracting pitch contour for entire track...")
        print("  This may take a while for long tracks...")
        sys.stdout.flush()

        # Extract pitch using pyin for entire track
        f0, voiced_flag, voiced_prob = librosa.pyin(
            y, fmin=self.fmin, fmax=self.fmax, sr=sr,
            frame_length=2048, hop_length=self.hop_length
        )

        # Convert to time
        times = librosa.times_like(f0, sr=sr, hop_length=self.hop_length)

        print(f"  Extracted {len(times)} pitch frames")
        voiced_count = np.sum(voiced_flag)
        print(f"  Voiced frames: {voiced_count} ({100*voiced_count/len(times):.1f}%)")

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

        print(f"  Saved to: {pitch_path.name}")

        print(f"\n{'=' * 50}")
        print("PITCH ESTIMATION COMPLETE")
        print(f"{'=' * 50}")

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
        import sys

        print(f"\n{'=' * 50}")
        print("PITCH ESTIMATION")
        print(f"{'=' * 50}")

        print("\n[1/3] Loading vocals...")
        y, sr = librosa.load(vocals_path, sr=None, mono=True)
        print(f"  Duration: {len(y)/sr:.1f} seconds")
        print(f"  Sample rate: {sr}Hz")

        output_dir = Path(output_dir)

        # Separate calls and responses
        calls = [s for s in sections if s['label'] == 'call']
        responses = [s for s in sections if s['label'] == 'response']

        # Match pairs
        n_pairs = min(len(calls), len(responses))
        print(f"\n[2/3] Extracting pitch contours for {n_pairs} pairs...")
        print(f"  Call sections: {len(calls)}")
        print(f"  Response sections: {len(responses)}")
        print(f"  Pairs to process: {n_pairs}")

        alignments = []

        for i in range(n_pairs):
            call = calls[i]
            response = responses[i]

            print(f"\n  Pair {i+1}/{n_pairs}:")
            print(f"    Call: {call['start']:.1f}s - {call['end']:.1f}s ({call['end']-call['start']:.1f}s)")
            print(f"    Response: {response['start']:.1f}s - {response['end']:.1f}s ({response['end']-response['start']:.1f}s)")
            sys.stdout.flush()

            # Extract call pitch
            print(f"    Extracting call pitch...")
            call_start = int(call['start'] * sr)
            call_end = int(call['end'] * sr)
            call_audio = y[call_start:call_end]
            call_pitch = self.extract_pitch_contour(call_audio, sr, call['start'])
            call_voiced = sum(1 for p in call_pitch if p['voiced'])
            print(f"      {len(call_pitch)} frames, {call_voiced} voiced ({100*call_voiced/len(call_pitch):.0f}%)")

            # Extract response pitch
            print(f"    Extracting response pitch...")
            resp_start = int(response['start'] * sr)
            resp_end = int(response['end'] * sr)
            resp_audio = y[resp_start:resp_end]
            response_pitch = self.extract_pitch_contour(resp_audio, sr, response['start'])
            resp_voiced = sum(1 for p in response_pitch if p['voiced'])
            print(f"      {len(response_pitch)} frames, {resp_voiced} voiced ({100*resp_voiced/len(response_pitch):.0f}%)")

            # Save pitch data
            call_path = output_dir / f"pitch_call_{i}.json"
            response_path = output_dir / f"pitch_response_{i}.json"

            with open(call_path, 'w') as f:
                json.dump(call_pitch, f)
            with open(response_path, 'w') as f:
                json.dump(response_pitch, f)

            # Calculate optimal alignment
            print(f"    Finding optimal alignment...")
            optimal_offset, correlation = self.find_optimal_offset(call_pitch, response_pitch)
            print(f"      Optimal offset: {optimal_offset:+.3f}s")
            print(f"      Correlation: {correlation:.3f}" if correlation else "      Correlation: N/A")

            alignments.append({
                'pair_id': i,
                'call_section_id': call['id'],
                'response_section_id': response['id'],
                'optimal_offset': float(optimal_offset),
                'correlation': float(correlation) if correlation is not None else None,
                'custom_offset': None
            })

            print(f"  Pair {i}: offset={optimal_offset:.3f}s, correlation={correlation:.3f if correlation else 'N/A'}")

        # Save alignments
        alignments_path = output_dir / "alignments.json"
        with open(alignments_path, 'w') as f:
            json.dump(alignments, f, indent=2)

        print(f"\n[3/3] Results:")
        print(f"  Pairs processed: {n_pairs}")
        print(f"  Alignments saved to: {alignments_path.name}")
        print(f"\n{'=' * 50}")
        print("PITCH ESTIMATION COMPLETE")
        print(f"{'=' * 50}")

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
