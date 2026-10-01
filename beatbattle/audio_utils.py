import numpy as np
import soundfile as sf

def load_audio(file_path: str, target_sr: int = 44100, mono: bool = False) -> tuple[np.ndarray, int]:
    """
    Loads audio file into a 2D numpy array (channels, samples).
    Supports .ogg and .wav via soundfile.
    """
    try:
        data, sr = sf.read(file_path, always_2d=True, dtype="float32")

        # Ensure multi-channel audio is averaged to mono if required by the downstream pipeline
        if mono:
            data = np.mean(data, axis=1, keepdims=True)

        # Convert to stereo if mono and mono is False
        elif data.shape[1] == 1:
            data = np.tile(data, (1, 2))

        data = data.T # Shape: (channels, samples)
    except Exception as sf_err:
        raise RuntimeError(f"Failed to read audio file {file_path} via soundfile. Error: {sf_err}")

    return data, sr
