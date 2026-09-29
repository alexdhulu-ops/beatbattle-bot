"""
Sample analysis and tagging.
"""
from typing import List, Dict, Any, Optional
import numpy as np
import os
import glob


class SampleLibrary:
    """
    Scans a root directory and maps specific sample folders to their audio files.
    """

    REQUIRED_FOLDERS = [
        "808s", "kicks", "claps", "snares", "hihats", "openhats",
        "percs_1", "percs_2", "synths_1", "synths_2", "synths_3",
        "fx_1", "fx_2", "Vox"
    ]

    CRITICAL_DRUMS = ["kicks", "808s", "hihats"]  # snares or claps are also critical, handled in logic
    SYNTH_FOLDERS = ["synths_1", "synths_2", "synths_3"]

    def __init__(self, root_dir: str):
        """
        Initializes the SampleLibrary and maps available files.

        Args:
            root_dir: The root directory containing the sample folders.
        """
        self.root_dir = root_dir
        self.library: Dict[str, str] = {}
        self._load_samples()
        self._validate_library()

    def _load_samples(self) -> None:
        """Loads the first .wav file found in each defined folder."""
        for folder in self.REQUIRED_FOLDERS:
            folder_path = os.path.join(self.root_dir, folder)
            if os.path.isdir(folder_path):
                # Grab the first wav file
                wav_files = glob.glob(os.path.join(folder_path, "*.wav"))
                if wav_files:
                    self.library[folder] = sorted(wav_files)[0]

    def _validate_library(self) -> None:
        """
        Validates that critical drums and at least one synth exist.
        Raises ValueError or FileNotFoundError if missing.
        """
        if "808s" not in self.library:
            raise FileNotFoundError("Strict 808s folder missing or contains no valid .wav file.")

        missing_critical = [drum for drum in self.CRITICAL_DRUMS if drum not in self.library]

        if "snares" not in self.library and "claps" not in self.library:
            missing_critical.append("snares/claps")

        if missing_critical:
            raise ValueError(f"Missing critical drums: {', '.join(missing_critical)}")

        has_synth = any(synth in self.library for synth in self.SYNTH_FOLDERS)
        if not has_synth:
            raise ValueError("Missing at least one synth folder with a valid .wav file.")

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
