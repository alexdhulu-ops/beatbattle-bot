"""
CLI entry point for beatbattle-bot.
"""
import typer
from typing import Optional
import time
import os
import random
import numpy as np
import soundfile as sf
from rich.console import Console
from rich.prompt import Prompt

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
) -> None:
    """
    Generates a new beatbattle song from a directory of samples.
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
    if not output_file.endswith(".wav"):
        output_file += ".wav"

    base_dir = os.path.dirname(output_file)
    if base_dir:
        os.makedirs(base_dir, exist_ok=True)

    seed = random.randint(1, 1_000_000)
    random.seed(seed)
    np.random.seed(seed)

    console.print("Generating Trap timeline...")
    timeline = arranger.create_timeline(library, variation_seed=seed)

    console.print("Rendering audio and applying mastering...")
    raw_audio = renderer.render_timeline(timeline)
    mastered_audio = mastering.process(raw_audio, 44100)

    # Ensure correct shape for soundfile (samples, channels)
    sf.write(output_file, mastered_audio.T, 44100)
    duration = mastered_audio.shape[1] / 44100.0
    console.print(f"[bold blue]Success![/bold blue] Saved '{output_file}' (Duration: {duration:.2f}s)")

    elapsed = time.time() - start_time
    console.print(f"Elapsed rendering time: {elapsed:.2f} seconds")


@app.command()
def analyze(
    file_path: str = typer.Argument(..., help="Path to the audio file to analyze"),
) -> None:
    """
    Analyzes a single audio file and prints its features.
    """
    pass


def main() -> None:
    """
    Entry point for the CLI application.
    """
    app()


if __name__ == "__main__":
    main()
