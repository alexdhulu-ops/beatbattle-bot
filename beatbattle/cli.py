"""
CLI entry point for beatbattle-bot.
"""
import typer
from typing import Optional
import time
import os
import numpy as np
import soundfile as sf
from rich.console import Console

from beatbattle.classifier import SampleLibrary
from beatbattle.arranger import TrapArranger
from beatbattle.renderer import AudioRenderer
from beatbattle.mastering import MasteringChain

app = typer.Typer(help="beatbattle-bot: An AI powered bot who plays beatbattle")
console = Console()

@app.command()
def generate(
    samples_dir: str = typer.Option(..., help="Directory containing audio samples"),
    output_file: str = typer.Option("output.wav", help="Path to save the generated song"),
    tempo: float = typer.Option(140.0, help="Tempo of the song in BPM"),
    batch: int = typer.Option(1, help="Number of distinct variations to generate in a batch"),
    seed: Optional[int] = typer.Option(None, help="Base seed for randomization"),
) -> None:
    """
    Generates a new beatbattle song (or batch of songs) from a directory of samples.
    """
    console.print("[bold green]Welcome to beatbattle-bot![/bold green]")

    if not os.path.exists(samples_dir):
        console.print(f"[bold red]Error:[/bold red] Directory '{samples_dir}' does not exist.")
        raise typer.Exit(code=1)

    start_time = time.time()

    # Initialize components
    console.print("Loading samples from directory...")
    library = SampleLibrary(samples_dir)
    arranger = TrapArranger(tempo=tempo)
    renderer = AudioRenderer(sample_rate=44100)
    mastering = MasteringChain(target_rms_db=-9.0, true_peak=-0.3)

    # Clean output path logic
    base_dir = os.path.dirname(output_file)
    base_name = os.path.basename(output_file)
    if base_dir:
        os.makedirs(base_dir, exist_ok=True)
    else:
        base_dir = "."

    if base_name.endswith(".wav"):
        base_name = base_name[:-4]

    unplayed_samples = set(library.library.keys())
    rng = np.random.default_rng(seed)
    base_seed = seed if seed is not None else rng.integers(1, 1_000_000)

    for i in range(batch):
        current_seed = int(base_seed + i * 7919)  # Large prime offset
        current_rng = np.random.default_rng(current_seed)

        console.print(f"Generating Trap timeline ({i + 1}/{batch})...")
        timeline = arranger.create_timeline(library, rng=current_rng, unplayed_samples=unplayed_samples)

        console.print(f"Rendering audio and applying mastering ({i + 1}/{batch})...")
        raw_audio = renderer.render_timeline(timeline)
        mastered_audio = mastering.process(raw_audio, 44100)

        if batch > 1:
            current_output = os.path.join(base_dir, f"{base_name}_{i + 1}.wav")
        else:
            current_output = os.path.join(base_dir, f"{base_name}.wav")

        # Ensure correct shape for soundfile (samples, channels)
        sf.write(current_output, mastered_audio.T, 44100)
        duration = mastered_audio.shape[1] / 44100.0
        console.print(f"[bold blue]Success![/bold blue] Saved '{current_output}' (Duration: {duration:.2f}s, Seed: {current_seed})")

    elapsed = time.time() - start_time
    console.print(f"Elapsed rendering time: {elapsed:.2f} seconds")


def main() -> None:
    """
    Entry point for the CLI application.
    """
    app()


if __name__ == "__main__":
    main()
