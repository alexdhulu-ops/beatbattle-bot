"""
Sample analysis and tagging.
"""
from typing import List, Dict, Any, Optional
import numpy as np
import os
import glob
import soundfile as sf


class SampleLibrary:
    """
    Scans a root directory (flat or nested) and maps files to sample roles based on keywords.
    """

    CRITICAL_DRUMS = ["kicks", "808s", "hihats", "snares"]

    def __init__(self, root_dir: str):
        """
        Initializes the SampleLibrary and maps available files.

        Args:
            root_dir: The root directory containing the sample files.
        """
        self.root_dir = root_dir
        self.library: Dict[str, str] = {}
        self._load_samples()
        self._validate_library()

    def _load_samples(self) -> None:
        """Recursively loads .mp3, .wav, and .ogg files and classifies them by keyword."""
        all_files = []
        valid_extensions = (".mp3", ".wav", ".ogg")
        for dirpath, _, filenames in os.walk(self.root_dir):
            for f in filenames:
                if f.lower().endswith(valid_extensions):
                    all_files.append(os.path.join(dirpath, f))

        # Sort files to ensure deterministic mapping (first matched file is kept)
        all_files.sort()

        for file_path in all_files:
            file_name = os.path.basename(file_path).lower()
            dir_name = os.path.basename(os.path.dirname(file_path)).lower()
            search_str = f"{dir_name}_{file_name}"

            # Map based on priority and keywords
            if "808" in search_str or "bass" in search_str or "sub" in search_str:
                self._add_to_library("808s", file_path)
            elif "kick" in search_str or "bd" in search_str:
                self._add_to_library("kicks", file_path)
            elif "open" in search_str or "openhat" in search_str or "oh" in search_str:
                self._add_to_library("open_hats", file_path)
            elif "hihat" in search_str or "hi_hat" in search_str or "hat" in search_str or "hh" in search_str:
                self._add_to_library("hihats", file_path)
            elif "snare" in search_str or "clap" in search_str or "rim" in search_str or "sd" in search_str:
                self._add_to_library("snares", file_path)
            elif "perc" in search_str:
                duration = self._get_duration(file_path)
                if duration < 1.2:
                    self._add_to_library("perc_oneshot", file_path)
                elif duration > 1.5:
                    self._add_to_library("perc_loop", file_path)
            elif "fx" in search_str or "riser" in search_str or "impact" in search_str:
                duration = self._get_duration(file_path)
                if duration < 1.2:
                    self._add_to_library("fx_oneshot", file_path)
                elif duration > 1.5:
                    self._add_to_library("fx_texture", file_path)
            elif any(kw in search_str for kw in ["vox", "vocal", "chant", "acapella", "adlib", "phrase"]):
                duration = self._get_duration(file_path)
                if duration < 1.2:
                    self._add_to_library("vox_oneshot", file_path)
                elif duration > 1.5:
                    self._add_to_library("vox_loop", file_path)
            elif any(kw in search_str for kw in ["loop", "melody", "sample", "synth", "pad", "flute"]):
                duration = self._get_duration(file_path)
                if duration < 0.5:
                    self._add_to_library("melody_oneshot", file_path)
                else:
                    self._add_to_library("melodies", file_path)

    def _get_duration(self, file_path: str) -> float:
        try:
            info = sf.info(file_path)
            return info.duration
        except Exception:
            return 0.0

    def _add_to_library(self, category: str, file_path: str):
        """Adds to library if not already populated to keep the first match."""
        if category not in self.library:
            self.library[category] = file_path

    def _validate_library(self) -> None:
        """
        Validates that critical drums and at least one melody exist.
        Raises ValueError or FileNotFoundError if missing.
        """
        if "808s" not in self.library:
            raise FileNotFoundError("Missing 808s sample (no valid audio file matching '808', 'bass', or 'sub').")

        missing_critical = [drum for drum in self.CRITICAL_DRUMS if drum not in self.library]
        if missing_critical:
            raise ValueError(f"Missing critical drums: {', '.join(missing_critical)}")

        if "melodies" not in self.library and "melody_oneshot" not in self.library:
            raise ValueError("Missing at least one melody/synth sample.")

    def get_sample(self, category: str) -> Optional[str]:
        """Gets the file path for a specific category."""
        return self.library.get(category)


class SampleClassifier:
    """
    Classifies audio samples into categories.
    """

    def __init__(self, model_path: str | None = None) -> None:
        """
        Initializes the SampleClassifier.

        Args:
            model_path: Optional path to a trained classification model.
        """
        pass

    def analyze_sample(self, file_path: str) -> Dict[str, Any]:
        """
        Analyzes a single audio file and extracts its features.

        Args:
            file_path: The path to the audio file.

        Returns:
            A dictionary containing the extracted features.
        """
        pass

    def tag_sample(self, features: Dict[str, Any]) -> List[str]:
        """
        Generates tags for a sample based on its features.

        Args:
            features: A dictionary of extracted features.

        Returns:
            A list of string tags describing the sample.
        """
        pass
