import os
import threading
import random
import time
import subprocess
import platform
import numpy as np
import soundfile as sf
import customtkinter as ctk
import pygame
from tkinter import filedialog

from beatbattle.classifier import SampleLibrary
from beatbattle.arranger import TrapArranger
from beatbattle.renderer import AudioRenderer
from beatbattle.mastering import MasteringChain

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class BeatBattleGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("beatbattle-bot")
        self.geometry("600x450")

        self.samples_dir = ctk.StringVar(value="")
        self.output_path = ctk.StringVar(value="output.wav")
        self.is_playing = False

        # Initialize pygame mixer for audio playback
        pygame.mixer.init()

        # Main container
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.main_frame = ctk.CTkFrame(self, corner_radius=10)
        self.main_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)

        # Title
        self.title_label = ctk.CTkLabel(self.main_frame, text="BeatBattle AI Generator", font=ctk.CTkFont(size=24, weight="bold"))
        self.title_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        # Sample Pack Selection
        self.pack_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.pack_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        self.pack_frame.grid_columnconfigure(0, weight=1)

        self.pack_label = ctk.CTkLabel(self.pack_frame, text="Sample Pack Directory:")
        self.pack_label.grid(row=0, column=0, sticky="w")

        self.pack_entry = ctk.CTkEntry(self.pack_frame, textvariable=self.samples_dir, state="disabled")
        self.pack_entry.grid(row=1, column=0, padx=(0, 10), pady=5, sticky="ew")

        self.pack_button = ctk.CTkButton(self.pack_frame, text="Browse...", width=100, command=self.browse_samples)
        self.pack_button.grid(row=1, column=1, pady=5)

        # Output Selection
        self.output_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.output_frame.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        self.output_frame.grid_columnconfigure(0, weight=1)

        self.output_label = ctk.CTkLabel(self.output_frame, text="Output File Path:")
        self.output_label.grid(row=0, column=0, sticky="w")

        self.output_entry = ctk.CTkEntry(self.output_frame, textvariable=self.output_path)
        self.output_entry.grid(row=1, column=0, padx=(0, 10), pady=5, sticky="ew")

        self.output_button = ctk.CTkButton(self.output_frame, text="Save As...", width=100, command=self.browse_output)
        self.output_button.grid(row=1, column=1, pady=5)

        # Generate Button
        self.generate_btn = ctk.CTkButton(self.main_frame, text="Generate Beat", font=ctk.CTkFont(size=18, weight="bold"), height=50, command=self.start_generation)
        self.generate_btn.grid(row=3, column=0, padx=20, pady=20, sticky="ew")

        # Status Label
        self.status_label = ctk.CTkLabel(self.main_frame, text="Ready", text_color="gray")
        self.status_label.grid(row=4, column=0, pady=(0, 10))

        # Post-generation controls
        self.controls_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.controls_frame.grid(row=5, column=0, padx=20, pady=(0, 20), sticky="ew")
        self.controls_frame.grid_columnconfigure((0, 1), weight=1)

        self.play_btn = ctk.CTkButton(self.controls_frame, text="▶ Play", state="disabled", command=self.toggle_playback)
        self.play_btn.grid(row=0, column=0, padx=(0, 10), sticky="ew")

        self.open_folder_btn = ctk.CTkButton(self.controls_frame, text="📁 Open Output Folder", state="disabled", command=self.open_output_folder)
        self.open_folder_btn.grid(row=0, column=1, padx=(10, 0), sticky="ew")

    def browse_samples(self):
        folder = filedialog.askdirectory(title="Select Sample Pack Directory")
        if folder:
            self.samples_dir.set(folder)

    def browse_output(self):
        file = filedialog.asksaveasfilename(
            defaultextension=".wav",
            filetypes=[("WAV files", "*.wav")],
            title="Save Output As"
        )
        if file:
            self.output_path.set(file)

    def start_generation(self):
        if not self.samples_dir.get():
            self.status_label.configure(text="Error: Please select a sample pack directory first.", text_color="red")
            return

        if not os.path.exists(self.samples_dir.get()):
            self.status_label.configure(text="Error: Sample directory does not exist.", text_color="red")
            return

        # Stop playback if playing
        if self.is_playing:
            self.toggle_playback()

        # Disable controls during generation
        self.generate_btn.configure(state="disabled")
        self.pack_button.configure(state="disabled")
        self.output_button.configure(state="disabled")
        self.play_btn.configure(state="disabled")
        self.open_folder_btn.configure(state="disabled")

        # Start thread
        threading.Thread(target=self.run_generation_pipeline, daemon=True).start()

    def run_generation_pipeline(self):
        try:
            self.update_status("Processing... Loading samples", "blue")

            samples_dir = self.samples_dir.get()
            out_file = self.output_path.get()
            if not out_file.endswith(".wav"):
                out_file += ".wav"

            base_dir = os.path.dirname(out_file)
            if base_dir:
                os.makedirs(base_dir, exist_ok=True)

            # Simulate slight delay so UI updates are visible
            time.sleep(0.1)

            library = SampleLibrary(samples_dir)
            arranger = TrapArranger(tempo=140.0)
            renderer = AudioRenderer(sample_rate=44100)
            mastering = MasteringChain(target_rms_db=-9.0, true_peak=-0.3)

            seed = random.randint(1, 1_000_000)
            random.seed(seed)
            np.random.seed(seed)

            self.update_status("Arranging timeline...", "blue")
            timeline = arranger.create_timeline(library, variation_seed=seed)

            self.update_status("Rendering audio...", "blue")
            raw_audio = renderer.render_timeline(timeline)

            self.update_status("Applying mastering...", "blue")
            mastered_audio = mastering.process(raw_audio, 44100)

            self.update_status("Saving file...", "blue")
            sf.write(out_file, mastered_audio.T, 44100)

            duration = mastered_audio.shape[1] / 44100.0

            # Re-enable controls and show success
            self.after(0, self.finish_generation, out_file, duration)

        except Exception as e:
            self.after(0, self.fail_generation, str(e))

    def update_status(self, text, color="gray"):
        self.after(0, lambda: self.status_label.configure(text=text, text_color=color))

    def finish_generation(self, out_file, duration):
        self.status_label.configure(text=f"Done! Saved '{os.path.basename(out_file)}' ({duration:.1f}s)", text_color="green")
        self.generate_btn.configure(state="normal")
        self.pack_button.configure(state="normal")
        self.output_button.configure(state="normal")
        self.play_btn.configure(state="normal")
        self.open_folder_btn.configure(state="normal")

        # Pre-load audio for playback
        try:
            pygame.mixer.music.load(out_file)
        except Exception as e:
            print(f"Failed to load audio in pygame: {e}")

    def fail_generation(self, error_msg):
        self.status_label.configure(text=f"Error: {error_msg}", text_color="red")
        self.generate_btn.configure(state="normal")
        self.pack_button.configure(state="normal")
        self.output_button.configure(state="normal")

    def toggle_playback(self):
        if not self.is_playing:
            pygame.mixer.music.play()
            self.play_btn.configure(text="⏹ Stop")
            self.is_playing = True

            # Simple check loop to reset button when song ends
            self.check_playback()
        else:
            pygame.mixer.music.stop()
            self.play_btn.configure(text="▶ Play")
            self.is_playing = False

    def check_playback(self):
        if self.is_playing:
            if not pygame.mixer.music.get_busy():
                self.play_btn.configure(text="▶ Play")
                self.is_playing = False
            else:
                self.after(100, self.check_playback)

    def open_output_folder(self):
        out_file = self.output_path.get()
        if not out_file.endswith(".wav"):
            out_file += ".wav"

        # Convert relative to absolute
        abs_path = os.path.abspath(out_file)
        folder = os.path.dirname(abs_path)

        if os.path.exists(folder):
            if platform.system() == "Windows":
                os.startfile(folder)
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", folder])
            else:
                subprocess.Popen(["xdg-open", folder])

def main():
    app = BeatBattleGUI()
    app.mainloop()

if __name__ == "__main__":
    main()
