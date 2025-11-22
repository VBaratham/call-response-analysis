"""Fingerprinting service - detects call/response sections using pitch-based features."""
import json
import uuid
from pathlib import Path
from typing import List, Tuple, Optional
import numpy as np
import librosa
from scipy.spatial.distance import euclidean
from scipy.ndimage import median_filter


class FingerprintingService:
    """Service for detecting call/response sections using vocal fingerprinting."""

    def __init__(self, hop_length: int = 512):
        self.hop_length = hop_length

    def extract_vocal_features(self, y: np.ndarray, sr: int) -> np.ndarray:
        """Extract features that discriminate between call and response voices."""

        # 1. PITCH - Most discriminative feature
        f0, voiced_flag, voiced_probs = librosa.pyin(
            y, fmin=80, fmax=500, sr=sr,
            frame_length=2048, hop_length=self.hop_length
        )

        # Use median pitch as key feature
        valid_f0 = f0[voiced_flag & ~np.isnan(f0)]
        if len(valid_f0) > 0:
            median_pitch = np.nanmedian(valid_f0)
            pitch_std = np.nanstd(valid_f0)
        else:
            median_pitch = 0
            pitch_std = 0

        # 2. Energy features
        rms = librosa.feature.rms(y=y, hop_length=self.hop_length)[0]
        energy = np.mean(rms)

        # 3. MFCC - reduced to 13 coefficients
        mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13, hop_length=self.hop_length)
        mfcc_mean = mfcc.mean(axis=1)

        # 4. Spectral features
        spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=self.hop_length)[0]
        spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr, hop_length=self.hop_length)[0]

        # 5. Spectral flux
        spec = np.abs(librosa.stft(y, hop_length=self.hop_length))
        spectral_flux = np.mean(np.sqrt(np.sum(np.diff(spec, axis=1)**2, axis=0)))

        # 6. Zero crossing rate
        zcr = librosa.feature.zero_crossing_rate(y=y, hop_length=self.hop_length)[0]

        # Combine features with pitch weighted heavily
        features = np.concatenate([
            [median_pitch * 10],  # Scale pitch for more weight
            [pitch_std],
            [energy * 100],
            mfcc_mean,
            [np.mean(spectral_centroid) / 1000],
            [np.mean(spectral_rolloff) / 1000],
            [spectral_flux],
            [np.mean(zcr) * 100]
        ])

        return features

    def build_fingerprint(self, y: np.ndarray, sr: int,
                         reference_sections: List[Tuple[float, float]]) -> np.ndarray:
        """Build a reference fingerprint from known sections."""
        all_features = []

        for start_time, end_time in reference_sections:
            start_sample = int(start_time * sr)
            end_sample = int(end_time * sr)
            segment = y[start_sample:end_sample]

            features = self.extract_vocal_features(segment, sr)
            all_features.append(features)

        return np.mean(all_features, axis=0)

    def compute_distances(self, y: np.ndarray, sr: int,
                         call_fingerprint: np.ndarray,
                         response_fingerprint: np.ndarray,
                         window_size: float = 2.0,
                         hop_size: float = 0.5) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Compute frame-by-frame distances to both fingerprints."""
        window_samples = int(window_size * sr)
        hop_samples = int(hop_size * sr)

        times = []
        call_distances = []
        response_distances = []

        for start_sample in range(0, len(y) - window_samples, hop_samples):
            end_sample = start_sample + window_samples
            window = y[start_sample:end_sample]

            features = self.extract_vocal_features(window, sr)

            call_dist = euclidean(features, call_fingerprint)
            response_dist = euclidean(features, response_fingerprint)

            time = start_sample / sr
            times.append(time)
            call_distances.append(call_dist)
            response_distances.append(response_dist)

        return np.array(times), np.array(call_distances), np.array(response_distances)

    def segment_by_distance(self, times: np.ndarray,
                           call_distances: np.ndarray,
                           response_distances: np.ndarray,
                           min_duration: float = 1.5) -> List[dict]:
        """Segment based on which fingerprint is closer."""
        # Smooth distances
        call_smooth = median_filter(call_distances, size=5)
        response_smooth = median_filter(response_distances, size=5)

        # Classify: call if closer to call fingerprint
        is_call = call_smooth < response_smooth

        # Find transitions
        transitions = np.diff(is_call.astype(int))

        # Find call sections
        call_starts = np.where(transitions == 1)[0]
        call_ends = np.where(transitions == -1)[0]

        if len(call_starts) > 0 and len(call_ends) > 0:
            if call_starts[0] > call_ends[0]:
                call_ends = call_ends[1:]
            if len(call_starts) > len(call_ends):
                call_starts = call_starts[:len(call_ends)]

        sections = []

        # Create call sections
        for start_idx, end_idx in zip(call_starts, call_ends):
            start_time = times[start_idx]
            end_time = times[end_idx]
            duration = end_time - start_time

            if duration >= min_duration:
                sections.append({
                    'id': f'section_{uuid.uuid4().hex[:8]}',
                    'start': float(start_time),
                    'end': float(end_time),
                    'label': 'call',
                    'is_reference': False,
                    'confidence': float(1.0 - call_smooth[start_idx:end_idx].mean() /
                                       (call_smooth[start_idx:end_idx].mean() +
                                        response_smooth[start_idx:end_idx].mean()))
                })

        # Find response sections
        response_starts = np.where(transitions == -1)[0]
        response_ends = np.where(transitions == 1)[0]

        if len(response_starts) > 0 and len(response_ends) > 0:
            if response_starts[0] > response_ends[0]:
                response_ends = response_ends[1:]
            if len(response_starts) > len(response_ends):
                response_starts = response_starts[:len(response_ends)]

        for start_idx, end_idx in zip(response_starts, response_ends):
            start_time = times[start_idx]
            end_time = times[end_idx]
            duration = end_time - start_time

            if duration >= min_duration:
                sections.append({
                    'id': f'section_{uuid.uuid4().hex[:8]}',
                    'start': float(start_time),
                    'end': float(end_time),
                    'label': 'response',
                    'is_reference': False,
                    'confidence': float(1.0 - response_smooth[start_idx:end_idx].mean() /
                                       (call_smooth[start_idx:end_idx].mean() +
                                        response_smooth[start_idx:end_idx].mean()))
                })

        # Sort by start time
        sections.sort(key=lambda x: x['start'])

        return sections

    def detect_sections(self, vocals_path: str, output_dir: Path,
                       call_references: Optional[List[Tuple[float, float]]] = None,
                       response_references: Optional[List[Tuple[float, float]]] = None) -> List[dict]:
        """
        Detect call/response sections in vocals.

        If no reference sections provided, uses automatic detection based on
        pitch differences (assumes call is lower pitch than response).
        """
        print(f"\n{'=' * 50}")
        print("SECTION DETECTION (FINGERPRINTING)")
        print(f"{'=' * 50}")

        print("\n[1/3] Loading vocals...")
        y, sr = librosa.load(vocals_path, sr=None, mono=True)
        duration = len(y) / sr
        print(f"  Duration: {duration:.1f} seconds")
        print(f"  Sample rate: {sr}Hz")
        print(f"  Samples: {len(y):,}")

        # If no references provided, use automatic initial segmentation
        if call_references is None or response_references is None:
            print("\n[2/3] Running automatic section detection...")
            print("  (No reference sections provided, using pitch-based clustering)")
            sections = self._auto_detect_sections(y, sr, duration)
        else:
            print("\n[2/3] Building fingerprints from references...")
            print(f"  Call references: {len(call_references)}")
            print(f"  Response references: {len(response_references)}")

            # Build fingerprints from provided references
            call_fingerprint = self.build_fingerprint(y, sr, call_references)
            response_fingerprint = self.build_fingerprint(y, sr, response_references)

            print("\n[3/3] Computing distances and segmenting...")
            # Compute distances
            times, call_dist, response_dist = self.compute_distances(
                y, sr, call_fingerprint, response_fingerprint
            )

            # Segment
            sections = self.segment_by_distance(times, call_dist, response_dist)

        # Save sections
        output_dir = Path(output_dir)
        sections_path = output_dir / "sections.json"
        with open(sections_path, 'w') as f:
            json.dump(sections, f, indent=2)

        # Summary
        calls = sum(1 for s in sections if s['label'] == 'call')
        responses = len(sections) - calls
        print(f"\n[3/3] Results:")
        print(f"  Total sections: {len(sections)}")
        print(f"  Call sections: {calls}")
        print(f"  Response sections: {responses}")
        print(f"\n{'=' * 50}")
        print("SECTION DETECTION COMPLETE")
        print(f"{'=' * 50}")

        return sections

    def _auto_detect_sections(self, y: np.ndarray, sr: int, duration: float) -> List[dict]:
        """
        Automatically detect sections without reference samples.

        Uses onset detection and pitch analysis to find vocal segments,
        then clusters by pitch to separate call from response.
        """
        import sys

        print("  Step 1: Detecting vocal activity regions...")
        # Detect onsets to find vocal activity regions
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        onsets = librosa.onset.onset_detect(onset_envelope=onset_env, sr=sr, units='time')
        print(f"    Found {len(onsets)} onset events")

        # Find segments with significant vocal activity using RMS
        print("  Step 2: Computing RMS energy...")
        rms = librosa.feature.rms(y=y, hop_length=512)[0]
        times = librosa.times_like(rms, sr=sr, hop_length=512)

        # Threshold for vocal activity (adaptive based on track)
        threshold = np.percentile(rms, 30)  # Above 30th percentile
        print(f"    RMS threshold (30th percentile): {threshold:.4f}")

        # Find contiguous regions above threshold
        is_active = rms > threshold
        changes = np.diff(is_active.astype(int))
        starts = np.where(changes == 1)[0]
        ends = np.where(changes == -1)[0]

        print(f"    Found {len(starts)} potential vocal regions")

        if len(starts) == 0:
            print("    WARNING: No vocal activity detected!")
            return []

        # Align starts and ends
        if len(ends) > 0 and (len(starts) == 0 or ends[0] < starts[0]):
            ends = ends[1:]
        if len(starts) > len(ends):
            starts = starts[:len(ends)]

        # Create initial segments with pitch analysis
        print(f"  Step 3: Analyzing pitch for each segment...")
        segments = []
        total_regions = len(starts)

        for i, (start_idx, end_idx) in enumerate(zip(starts, ends)):
            start_time = times[start_idx]
            end_time = times[end_idx]
            duration_seg = end_time - start_time

            if duration_seg >= 1.0:  # Minimum 1 second
                # Progress indicator
                if (i + 1) % 10 == 0 or i == total_regions - 1:
                    print(f"    Analyzing segment {i+1}/{total_regions}...")
                    sys.stdout.flush()

                # Extract segment and compute pitch
                start_sample = int(start_time * sr)
                end_sample = int(end_time * sr)
                segment = y[start_sample:end_sample]

                # Get median pitch for this segment
                f0, voiced, _ = librosa.pyin(segment, fmin=80, fmax=500, sr=sr)
                valid_f0 = f0[voiced & ~np.isnan(f0)]

                if len(valid_f0) > 10:
                    median_pitch = np.median(valid_f0)
                    segments.append({
                        'start': start_time,
                        'end': end_time,
                        'pitch': median_pitch
                    })

        print(f"    Analyzed {len(segments)} segments with valid pitch data")

        if len(segments) < 2:
            print(f"    WARNING: Only {len(segments)} segments found, not enough to classify")
            # Return all as call sections
            return [{
                'id': f'section_{uuid.uuid4().hex[:8]}',
                'start': s['start'],
                'end': s['end'],
                'label': 'call',
                'is_reference': False,
                'confidence': 0.5
            } for s in segments]

        # Cluster segments by pitch (simple median split)
        print("  Step 4: Clustering by pitch...")
        pitches = [s['pitch'] for s in segments]
        median_pitch = np.median(pitches)
        print(f"    Median pitch threshold: {median_pitch:.1f} Hz")
        print(f"    Pitch range: {min(pitches):.1f} - {max(pitches):.1f} Hz")

        sections = []
        for seg in segments:
            # Lower pitch = call, higher pitch = response
            label = 'call' if seg['pitch'] < median_pitch else 'response'
            confidence = abs(seg['pitch'] - median_pitch) / median_pitch  # Higher diff = more confident

            sections.append({
                'id': f'section_{uuid.uuid4().hex[:8]}',
                'start': float(seg['start']),
                'end': float(seg['end']),
                'label': label,
                'is_reference': False,
                'confidence': float(min(0.9, confidence))  # Cap at 0.9
            })

        print(f"Auto-detected {len(sections)} sections")
        calls = sum(1 for s in sections if s['label'] == 'call')
        responses = len(sections) - calls
        print(f"  - {calls} call sections")
        print(f"  - {responses} response sections")

        return sections

    def propose_references(self, sections: List[dict], top_n: int = 3) -> dict:
        """
        Propose candidate reference sections based on confidence scores.

        Returns highest-confidence sections for both call and response.
        """
        calls = [s for s in sections if s['label'] == 'call']
        responses = [s for s in sections if s['label'] == 'response']

        # Sort by confidence
        calls.sort(key=lambda x: x.get('confidence', 0), reverse=True)
        responses.sort(key=lambda x: x.get('confidence', 0), reverse=True)

        return {
            'call_candidates': calls[:top_n],
            'response_candidates': responses[:top_n]
        }
