"""
CLI entry point for beatbattle-bot.
"""
import typer
from typing import Optional


app = typer.Typer(help="beatbattle-bot: An AI powered bot who plays beatbattle")


@app.command()
def generate(
    samples_dir: str = typer.Option(..., help="Directory containing audio samples"),
    output_file: str = typer.Option("output.wav", help="Path to save the generated song"),
    tempo: float = typer.Option(120.0, help="Tempo of the song in BPM"),
) -> None:
    """
    Generates a new beatbattle song from a directory of samples.
    """
    pass


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
