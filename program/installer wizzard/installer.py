import emoji
from customtkinter import CTkImage
from PIL import Image, ImageDraw, ImageFont
def emoji_(emoji, size=32):
    # Convert emoji to CTkImage
    font = ImageFont.truetype("seguiemj.ttf", size=int(size/1.5))
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.text((size/2, size/2), emoji, embedded_color=True, font=font, anchor="mm")
    img = CTkImage(img, size=(size, size))
    return img


import os
import sys
import customtkinter as ctk
from tkinter import filedialog, messagebox
import requests
import shutil
import threading
import zipfile
import time

GITHUB_MAIN_URL = "https://github.com/suskese/Video-Downloader/releases/latest/download/Video Downloader.exe"
YT_DLP_URL = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
FFMPEG_ZIP_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"

if sys.platform == "win32":
	DEFAULT_INSTALL_DIR = os.path.join(os.environ.get("APPDATA", r"C:\\Users\\Public\\AppData\\Roaming"), "Video Downloader")
else:
	DEFAULT_INSTALL_DIR = os.path.expanduser(r"~/Video Downloader")

class InstallerWizard(ctk.CTk):
	def __init__(self):
		super().__init__()
		ctk.set_appearance_mode("System")
		ctk.set_default_color_theme("blue")
		self.title("Video Downloader Installer Wizard")
		self.geometry("600x250")
		self.resizable(False, False)
		self.install_dir = ctk.StringVar(value=DEFAULT_INSTALL_DIR)
		self.create_shortcut = ctk.BooleanVar(value=True)
		self.create_startmenu = ctk.BooleanVar(value=True)
		self.step = 0
		self.steps = [self.step_select_dir, self.step_shortcuts, self.step_installing, self.step_finish]
		# Use a label with a larger font and fallback to image if emoji not supported
		try:
			self.emoji_label = ctk.CTkLabel(self, image=emoji_("📦",size=128),text="", font=("Segoe UI Emoji", 60, "bold"))
		except Exception:
			self.emoji_label = ctk.CTkLabel(self, text="[ ]", font=("Segoe UI", 60, "bold"))
		self.emoji_label.grid(row=0, column=0, rowspan=2, padx=(30, 10), pady=(60, 10), sticky="n")
		self.right_frame = ctk.CTkFrame(self, fg_color="transparent")
		self.right_frame.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=(0, 0), pady=(0, 0))
		self.grid_columnconfigure(1, weight=1)
		self.grid_rowconfigure(0, weight=1)
		self.next_button = ctk.CTkButton(self, text="Next", command=self.next_step, font=("Segoe UI", 14, "bold"), width=100, height=40)
		# More appealing colors for the main navigation buttons
		self.next_button = ctk.CTkButton(self, text="Next", command=self.next_step, font=("Segoe UI", 14, "bold"), width=100, height=40, fg_color="#1f6aa5", text_color="white")
		self.next_button.grid(row=2, column=1, sticky="e", padx=(0, 30), pady=(10, 20))
		self.back_button = ctk.CTkButton(self, text="Back", command=self.prev_step, font=("Segoe UI", 14, "bold"), width=100, height=40, fg_color="#1b5988", text_color="white")
		self.back_button.grid(row=2, column=1, sticky="e", padx=(120, 140), pady=(10, 20))
		# Lower status label (was green) — use white for better contrast on dark themes
		self.status_label = ctk.CTkLabel(self, text="", font=("Segoe UI", 11, "bold"), text_color="white")
		self.status_label.grid(row=1, column=1, sticky="sw", padx=(10, 0), pady=(0, 10))
		self.launch_button = None
		self.close_button = None
		self.show_step()

	def show_step(self):
		for widget in self.right_frame.winfo_children():
			widget.destroy()
		# Hide launch/close buttons if not on finish step
		if self.launch_button:
			self.launch_button.grid_remove()
		if self.close_button:
			self.close_button.grid_remove()
		self.steps[self.step]()
		if self.step == 3:
			self.next_button.grid_remove()
			self.back_button.grid_remove()
			if not self.launch_button:
				self.launch_button = ctk.CTkButton(self, text="Launch Program", command=self.launch_program, font=("Segoe UI", 14, "bold"), fg_color="#1f6aa5", text_color="white", width=140, height=40)
			if not self.close_button:
				self.close_button = ctk.CTkButton(self, text="Close Installer", command=self.destroy, font=("Segoe UI", 14, "bold"), width=140, height=40)
			self.launch_button.grid(row=2, column=1, sticky="e", padx=(0, 190), pady=(10, 20))
			self.close_button.grid(row=2, column=1, sticky="e", padx=(160, 30), pady=(10, 20))
		else:
			self.next_button.grid()
			self.back_button.grid()
			if self.launch_button:
				self.launch_button.grid_remove()
			if self.close_button:
				self.close_button.grid_remove()
		# Keep Next/Back disabled during the actual installation step so the user can't navigate away
		if self.step == 2:
			self.next_button.configure(state="disabled")
			self.back_button.configure(state="disabled")
		else:
			self.back_button.configure(state="normal" if self.step > 0 else "disabled")
			self.next_button.configure(state="normal")

	def next_step(self):
		if self.step < len(self.steps) - 1:
			self.step += 1
			self.show_step()

	def prev_step(self):
		if self.step > 0:
			self.step -= 1
			self.show_step()

	def step_select_dir(self):
		ctk.CTkLabel(self.right_frame, text="Select the installation directory", font=("Segoe UI", 20, "bold"), text_color="#1f6aa5").pack(anchor="w", pady=(30, 5), padx=(10, 0))
		ctk.CTkLabel(self.right_frame, text="Choose where to install Video Downloader.", font=("Segoe UI", 13, "bold")).pack(anchor="w", pady=(0, 10), padx=(10, 0))
		entry = ctk.CTkEntry(self.right_frame, textvariable=self.install_dir, font=("Segoe UI", 13, "bold"), width=400)
		entry.pack(anchor="w", pady=(0, 5), padx=(10, 0))
		ctk.CTkButton(self.right_frame, text="Browse",font=("Segoe UI", 13, "bold"),command=self.browse_dir, width=100).pack(anchor="w", padx=(10, 0))

	def browse_dir(self):
		dir_selected = filedialog.askdirectory(initialdir=self.install_dir.get(), title="Select Install Directory")
		if dir_selected:
			# If selected dir is not empty, create a subfolder
			if os.path.isdir(dir_selected) and os.listdir(dir_selected):
				subfolder = os.path.join(dir_selected, "Video Downloader")
				count = 1
				while os.path.exists(subfolder):
					subfolder = os.path.join(dir_selected, f"Video Downloader {count}")
					count += 1
				os.makedirs(subfolder, exist_ok=True)
				self.install_dir.set(subfolder)
			else:
				self.install_dir.set(dir_selected)

	def step_shortcuts(self):
		ctk.CTkLabel(self.right_frame, text="Create Shortcuts", font=("Segoe UI", 18, "bold"), text_color="#1f6aa5").pack(anchor="w", pady=(30, 5), padx=(10, 0))
		ctk.CTkLabel(self.right_frame, text="Choose where to create shortcuts.", font=("Segoe UI", 13, "bold")).pack(anchor="w", pady=(0, 10), padx=(10, 0))
		ctk.CTkCheckBox(self.right_frame, text="Desktop Shortcut", variable=self.create_shortcut, font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=(10, 0))
		ctk.CTkCheckBox(self.right_frame, text="Start Menu Shortcut", variable=self.create_startmenu, font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=(10, 0))

	def step_installing(self):
		ctk.CTkLabel(self.right_frame, text="Installing...", font=("Segoe UI", 20, "bold"), text_color="#1f6aa5").pack(anchor="w", pady=(30, 5), padx=(10, 0))
		self.progress = ctk.CTkProgressBar(self.right_frame, orientation="horizontal", width=400)
		self.progress.pack(anchor="w", pady=(10, 10), padx=(10, 0))
		self.progress.set(0)
		self.status = ctk.CTkLabel(self.right_frame, text="", font=("Segoe UI", 13, "bold"))
		self.status.pack(anchor="w", padx=(10, 0))
		self.next_button.configure(state="disabled")
		self.back_button.configure(state="disabled")
		threading.Thread(target=self.do_install, daemon=True).start()

	def step_finish(self):
		# Create a horizontal container so the emoji image appears to the left of the text
		container = ctk.CTkFrame(self.right_frame, fg_color="transparent")
		container.pack(anchor="w", pady=(30, 5), padx=(10, 0))
		img_label = ctk.CTkLabel(container, image=emoji_("🎉", size=32), text="")
		img_label.pack(side="left")
		text_label = ctk.CTkLabel(container, text="Installation Complete!", font=("Segoe UI", 22, "bold"), text_color="green")
		text_label.pack(side="left", padx=(8, 0))
		ctk.CTkLabel(self.right_frame, text="Video Downloader has been installed.", font=("Segoe UI", 14)).pack(anchor="w", pady=(0, 10), padx=(10, 0))
		# Buttons are now shown in show_step()

	def do_install(self):
		try:
			import shutil as _shutil
			install_dir = self.install_dir.get()
			libs_dir = os.path.join(install_dir, 'libs')
			os.makedirs(libs_dir, exist_ok=True)

			# Handle bundled py files to be moved as pyd
			if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
				base_path = sys._MEIPASS
			else:
				base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'emoji builder'))

			# copy core_update.py to libs/core_update.pyd
			core_update_src = os.path.join(base_path, 'core_update.py')
			core_update_dst = os.path.join(libs_dir, 'core_update.pyd')
			_shutil.copy(core_update_src, core_update_dst)

			# copy emoji.py to libs/emoji.pyd
			emoji_src = os.path.join(base_path, 'emoji1.py')
			emoji_dst = os.path.join(libs_dir, 'emoji.pyd')
			_shutil.copy(emoji_src, emoji_dst)

			self.update_progress(10, "Downloading main program...")
			main_exe_path = os.path.join(install_dir, 'Video Downloader.exe')
			try:
				self.download_file(GITHUB_MAIN_URL, main_exe_path, lambda p, d, t, s, r: self._update_download_status(10, 20, "main program", p, d, t, s, r))
			except Exception:
				# fallback to attached.py
				if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
					base_path = sys._MEIPASS
				else:
					base_path = os.path.dirname(__file__)
				attached_path = os.path.join(base_path, 'attached.py')
				shutil.copy(attached_path, main_exe_path)
			self.update_progress(30, "Downloading yt-dlp.exe...")
			yt_dlp_path = os.path.join(libs_dir, 'yt-dlp.exe')
			self.download_file(YT_DLP_URL, yt_dlp_path, lambda p, d, t, s, r: self._update_download_status(30, 30, "yt-dlp", p, d, t, s, r))
			# Check for ffmpeg in PATH
			ffmpeg_in_path = _shutil.which('ffmpeg')
			if ffmpeg_in_path:
				self.update_progress(80, f"ffmpeg found in PATH, skipping download.")
			else:
				self.update_progress(60, "Downloading ffmpeg...")
				ffmpeg_zip = os.path.join(libs_dir, 'ffmpeg.zip')
				self.download_file(FFMPEG_ZIP_URL, ffmpeg_zip, lambda p, d, t, s, r: self._update_download_status(60, 20, "ffmpeg", p, d, t, s, r))
				self.update_progress(80, "Extracting ffmpeg...")
				self.extract_ffmpeg(ffmpeg_zip, libs_dir)
				os.remove(ffmpeg_zip)
			self.update_progress(90, "Creating shortcuts...")
			self.create_shortcuts(install_dir, main_exe_path)
			self.update_progress(100, "Done!")
			self.next_button.configure(state="normal")
			self.back_button.configure(state="disabled")
			self.step = 3
			self.show_step()
		except Exception as e:
			self.status.configure(text=f"Error: {e}", text_color="red")

	def _update_download_status(self, base_progress, progress_range, name, percent, downloaded_size, total_size, speed, remaining_time):
		overall_progress = base_progress + (percent / 100) * progress_range
		if total_size > 0:
			# Format speed
			if speed >= 1024 * 1024:
				speed_str = f"{speed / (1024 * 1024):.1f} MB/s"
			else:
				speed_str = f"{speed / 1024:.0f} KB/s"

			# Format time
			if remaining_time > 60:
				mins = int(remaining_time / 60)
				secs = int(remaining_time % 60)
				time_str = f"{mins}m {secs:02d}s"
			else:
				time_str = f"{int(remaining_time)}s"

			status_text = (f"Downloading {name}: {downloaded_size/1024/1024:.1f}/{total_size/1024/1024:.1f}MB ({percent:.0f}%) "
						   f"{speed_str}, ETA: {time_str}")
		else:
			status_text = f"Downloading {name}... ({downloaded_size/1024/1024:.2f} MB)"
		self.update_progress(overall_progress, status_text)

	def update_progress(self, value, text):
		self.progress.set(value / 100)
		self.status.configure(text=text)
		self.status_label.configure(text=text)
		self.update_idletasks()

	def download_file(self, url, dest, progress_callback=None):
		r = requests.get(url, stream=True)
		r.raise_for_status()
		total_size = int(r.headers.get('content-length', 0))
		downloaded_size = 0
		start_time = time.time()
		last_update = start_time
		with open(dest, 'wb') as f:
			for chunk in r.iter_content(chunk_size=8192):
				if chunk:
					f.write(chunk)
					downloaded_size += len(chunk)
					now = time.time()
					if progress_callback and (now - last_update > 0.2 or downloaded_size == total_size):
						last_update = now
						elapsed_time = now - start_time
						if elapsed_time > 0:
							speed = downloaded_size / elapsed_time
							remaining_time = (total_size - downloaded_size) / speed if speed > 0 else 0
							percent = (downloaded_size / total_size) * 100 if total_size > 0 else 0
							progress_callback(percent, downloaded_size, total_size, speed, remaining_time)

	def extract_ffmpeg(self, zip_path, libs_dir):
		with zipfile.ZipFile(zip_path, 'r') as zip_ref:
			for member in zip_ref.namelist():
				if member.endswith('ffmpeg.exe'):
					zip_ref.extract(member, libs_dir)
					# Move ffmpeg.exe to libs_dir root
					src = os.path.join(libs_dir, member)
					dst = os.path.join(libs_dir, 'ffmpeg.exe')
					shutil.move(src, dst)
					# Remove extracted folders
					extracted_folder = os.path.join(libs_dir, member.split('/')[0])
					if os.path.isdir(extracted_folder):
						shutil.rmtree(extracted_folder)
					break

	def create_shortcuts(self, install_dir, exe_path):
		try:
			import winshell
			from win32com.client import Dispatch
			desktop = winshell.desktop()
			startmenu = winshell.start_menu()
			if self.create_shortcut.get():
				shortcut = os.path.join(desktop, "Video Downloader.lnk")
				self.make_shortcut(exe_path, shortcut)
			if self.create_startmenu.get():
				shortcut = os.path.join(startmenu, "Video Downloader.lnk")
				self.make_shortcut(exe_path, shortcut)
		except ImportError:
			pass  # Optionally show a warning

	def make_shortcut(self, target, shortcut_path):
		from win32com.client import Dispatch
		shell = Dispatch('WScript.Shell')
		shortcut = shell.CreateShortCut(shortcut_path)
		shortcut.Targetpath = target
		shortcut.WorkingDirectory = os.path.dirname(target)
		shortcut.save()

	def launch_program(self):
		exe_path = os.path.join(self.install_dir.get(), 'Video Downloader.exe')
		if os.path.exists(exe_path):
			os.startfile(exe_path)
		self.destroy()

if __name__ == "__main__":
	app = InstallerWizard()
	app.mainloop()
