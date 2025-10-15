
import os
import sys
import threading
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
import subprocess
import emoji
from PIL import Image, ImageDraw, ImageFont

if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)
    if application_path not in sys.path:
        sys.path.insert(0, application_path)
else:
    # Running as a script from source
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

try:
	from libs.emoji import emoji_
	import libs.core_update
except Exception as e:
	print(f"Failed to load emoji library: {e}")
	# Define a fallback function so the app doesn't crash.
	def emoji_(symbol, size):
		return None

def resource_path(relative):
	# Support PyInstaller --onefile
	if hasattr(sys, '_MEIPASS'):
		return os.path.join(sys._MEIPASS, relative)
	return os.path.join(os.path.dirname(__file__), relative)

UPDATER_PATH = resource_path('updater.py')
DOWNLOADER_PATH = resource_path('downloader.py')

class UpdateWindow(ctk.CTk):
	def __init__(self):
		super().__init__()
		ctk.set_appearance_mode("System")
		ctk.set_default_color_theme("dark-blue")
		self.title("Checking for Updates")
		self.geometry("480x180")
		self.resizable(False, False)

		# Top row: emoji + title
		header_frame = ctk.CTkFrame(self, fg_color="transparent")
		header_frame.pack(fill="x", pady=(12, 6), padx=12)
		emoji_label = ctk.CTkLabel(header_frame, image=emoji_("🔄", size=36), text="") 
		emoji_label.pack(side="left", padx=(6, 12))
		title_label = ctk.CTkLabel(header_frame, text="Checking for Updates", font=("Segoe UI", 16, "bold"))
		title_label.pack(side="left", anchor="w")

		# Progress area
		self.status_label = ctk.CTkLabel(self, text="Checking for updates...", font=("Segoe UI", 12))
		self.status_label.pack(pady=(6, 6))
		self.progress = ctk.CTkProgressBar(self, orientation="horizontal")
		self.progress.pack(fill="x", padx=20, pady=(0, 10))
		self.progress.start()

		# Action buttons (hidden until done)
		self.button_frame = ctk.CTkFrame(self, fg_color="transparent")
		self.button_frame.pack(fill="x", pady=(6, 12), padx=20)
		self.launch_btn = ctk.CTkButton(self.button_frame, text="Launch App", command=self.launch_main, fg_color="#1f6aa5", text_color="white", width=140)
		self.quit_btn = ctk.CTkButton(self.button_frame, text="Close", command=self.destroy, width=100)
		# initially hide
		self.launch_btn.pack_forget()
		self.quit_btn.pack_forget()

		# Start background update check
		threading.Thread(target=self.run_update, daemon=True).start()

	def run_update(self):
		"""Run updater quickly in background and update UI on completion."""
		try:
			if hasattr(sys, '_MEIPASS'):
				# Running as a bundled executable, import and run updater directly
				from updater import update_yt_dlp, update_main_program
				update_yt_dlp()
				update_main_program()
				self.after(0, lambda: self.on_update_success("Update complete."))
			else:
				# Running as a script, use subprocess
				proc = subprocess.run([sys.executable, UPDATER_PATH], capture_output=True, text=True, timeout=30)
				if proc.returncode == 0:
					# quick success
					self.after(0, lambda: self.on_update_success(proc.stdout))
				else:
					self.after(0, lambda: self.on_update_failure(proc.stderr))
		except subprocess.TimeoutExpired:
			self.after(0, lambda: self.on_update_failure("Update check timed out."))
		except Exception as e:
			self.after(0, lambda: self.on_update_failure(str(e)))

	def on_update_success(self, output):
		self.progress.stop()
		self.progress.set(1.0)
		self.status_label.configure(text="Update check complete. Launching app...")
		# hide any buttons and auto-launch after a short delay
		for w in self.button_frame.winfo_children():
			w.pack_forget()
		self.after(500, self.launch_main)

	def on_update_failure(self, error_text):
		self.progress.stop()
		# Show the error in the UI and then auto-launch the app so the user isn't blocked
		self.status_label.configure(text="Update check failed — opening app anyway.")
		# Optionally include the error in the title bar or console for debugging
		print("Updater error:", error_text)
		for w in self.button_frame.winfo_children():
			w.pack_forget()
		# Auto-launch after a short pause so user sees the message
		self.after(1000, self.launch_main)

	def launch_main(self):
		self.destroy()
		try:
			import downloader
			downloader.main()
		except Exception as e:
			messagebox.showerror("Launch Error", str(e))

if __name__ == "__main__":
	app = UpdateWindow()
	app.mainloop()
	