import numpy as np
import soundfile as sf
import pydub

def load_audio(file_path: str, target_sr: int = 44100) -> tuple[np.ndarray, int]:
    """
    Loads audio file into a 2D numpy array (channels, samples).
    Supports .mp3, .ogg, .wav via soundfile, with pydub fallback for arbitrary formats.
    """
    try:
        data, sr = sf.read(file_path, always_2d=True)
        # Convert to stereo if mono
        if data.shape[1] == 1:
            data = np.tile(data, (1, 2))
        data = data.T # Shape: (channels, samples)
    except Exception as sf_err:
        try:
            # Fallback to pydub for tricky formats like some MP3s without proper libsndfile support
            audio_seg = pydub.AudioSegment.from_file(file_path)

            # Ensure proper sample rate
            if audio_seg.frame_rate != target_sr:
                audio_seg = audio_seg.set_frame_rate(target_sr)

            sr = audio_seg.frame_rate

            # Get raw numpy array
            channel_data = np.array(audio_seg.get_array_of_samples())

            # Reshape based on channels
            if audio_seg.channels == 2:
                channel_data = channel_data.reshape((-1, 2)).T
            else:
                channel_data = channel_data.reshape((1, -1))
                channel_data = np.tile(channel_data, (2, 1))

            # Normalize to -1.0 to 1.0 (assuming 16-bit by default for pydub)
            data = channel_data.astype(np.float32) / (2 ** (8 * audio_seg.sample_width - 1))
        except Exception as pydub_err:
            raise RuntimeError(f"Failed to read audio file {file_path}. Soundfile error: {sf_err}. Pydub error: {pydub_err}")

    return data, sr
