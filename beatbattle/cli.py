"""
CLI entry point for beatbattle-bot.
"""
import typer
from typing import Optional
import time
import os
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
def generate() -> None:
    """
    Generates a new beatbattle song interactively.
    """
    console.print("[bold green]Welcome to beatbattle-bot![/bold green]")

    # Prompt for samples directory
    raw_path = Prompt.ask("Enter or drag-and-drop the unzipped samples folder path")
    # Strip quotes, backslashes, and leading/trailing whitespace
    samples_dir = raw_path.strip().strip("'").strip('"').replace("\\ ", " ").replace("\\", "")

    if not os.path.exists(samples_dir):
        console.print(f"[bold red]Error:[/bold red] Directory '{samples_dir}' does not exist.")
        raise typer.Exit(code=1)

    duration = Prompt.ask("Enter battle duration in minutes (e.g., 15 or 20)", default="15")
    try:
        duration_mins = int(duration)
    except ValueError:
        console.print("[bold red]Error:[/bold red] Duration must be an integer.")
        raise typer.Exit(code=1)

    start_time = time.time()

    # Initialize components
    console.print("Loading samples...")
    library = SampleLibrary(samples_dir)
    arranger = TrapArranger()
    renderer = AudioRenderer(sample_rate=44100)
    mastering = MasteringChain(target_lufs=-9.0, true_peak=-0.3)

    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)

    variations = 1 if duration_mins <= 15 else 3

    for i in range(variations):
        v_idx = i + 1
        console.print(f"Generating variation {v_idx}/{variations}...")

        timeline = arranger.create_timeline(library, variation_seed=v_idx)
        raw_audio = renderer.render_timeline(timeline)
        mastered_audio = mastering.process(raw_audio, 44100)

        output_file = os.path.join(output_dir, f"trap_beat_v{v_idx}.wav")
        # Ensure correct shape for soundfile (samples, channels)
        sf.write(output_file, mastered_audio.T, 44100)
        console.print(f"Saved: {output_file}")

    elapsed = time.time() - start_time
    console.print(f"[bold blue]Execution Summary:[/bold blue]")
    console.print(f"Rendered {variations} track(s) to '{output_dir}/'")
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
