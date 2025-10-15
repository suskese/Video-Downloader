import customtkinter as ctk
from tkinter import filedialog, messagebox
import time
import re
import shutil
import subprocess
import threading
import os
import sys

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

if hasattr(sys, '_MEIPASS'):
	BASE_DIR = os.path.dirname(sys.executable)
else:
	BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DOWNLOAD_DIR = os.path.join(BASE_DIR, 'downloaded')
if not os.path.exists(DEFAULT_DOWNLOAD_DIR):
	os.makedirs(DEFAULT_DOWNLOAD_DIR)

def get_libs_dir():
	import sys, os
	if hasattr(sys, '_MEIPASS'):
		return os.path.join(os.path.dirname(sys.executable), 'libs')
	return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'libs'))

def sanitize_filename(filename):
	filename = re.sub(r'[<>:"/\\|?*]', '', filename)
	filename = filename.replace(' ', '_')
	return filename[:200]


class DownloaderApp(ctk.CTk):
	def __init__(self):
		self.resolved_video_url = None  # Store resolved URL for download
		super().__init__()
		self.title("Video Downloader")
		self.geometry("700x600")
		self.resizable(False, False)
		ctk.set_appearance_mode("dark")
		ctk.set_default_color_theme("dark-blue")

		self.download_dir = DEFAULT_DOWNLOAD_DIR
		self.url_var = ctk.StringVar()
		self.status_var = ctk.StringVar(value="Ready.")
		self.progress_var = ctk.DoubleVar(value=0.0)
		self.fragment_enabled = ctk.BooleanVar(value=False)
		self.start_time_var = ctk.StringVar(value="00:00:00")
		self.end_time_var = ctk.StringVar(value="00:00:00")


		self.create_widgets()

	def create_widgets(self):
		# --- UI Layout: match VideoDownloaderUI ---
		self.grid_rowconfigure(0, weight=0)
		self.grid_rowconfigure(1, weight=0)
		self.grid_rowconfigure(2, weight=1)
		self.grid_rowconfigure(3, weight=0)
		self.grid_rowconfigure(4, weight=0)
		self.grid_rowconfigure(5, weight=0)
		self.grid_rowconfigure(6, weight=0)
		self.grid_columnconfigure(0, weight=1)

		# Top controls (URL/search)
		top_controls_frame = ctk.CTkFrame(self, fg_color="transparent")
		top_controls_frame.grid(row=0, column=0, columnspan=2, padx=20, pady=(20, 10), sticky="ew")
		top_controls_frame.grid_columnconfigure(0, weight=1)
		top_controls_frame.grid_columnconfigure(1, weight=0)
		# Make placeholder text visible by specifying a placeholder color
		# NOTE: binding textvariable to CTkEntry can prevent placeholder rendering in some CTk versions.
		# To ensure placeholder shows, create the entry without textvariable and sync manually.
		self.url_entry = ctk.CTkEntry(top_controls_frame, placeholder_text="Search video by name or URL", placeholder_text_color="#8a8a8a", font=ctk.CTkFont(size=14, weight="bold"))
		# Keep the StringVar in sync with the entry content
		self.url_entry.bind('<KeyRelease>', lambda e: self.url_var.set(self.url_entry.get()))
		self.url_entry.grid(row=0, column=0, padx=(0, 10), sticky="ew")
		self.setup_right_click_menu()
		self.url_entry.bind("<Return>", lambda e: self.start_search_thread())
		self.search_button = ctk.CTkButton(top_controls_frame,image=emoji_("🔍", size=22), text="Search", command=self.start_search_thread, fg_color="#1f6aa5", hover_color="#2a8cdb", font=ctk.CTkFont(size=14, weight="bold"), height=20)
		self.search_button.grid(row=0, column=1, sticky="e")
		# Video info label
		self.video_info_label = ctk.CTkLabel(self, text="", anchor="w", justify="left", font=ctk.CTkFont(size=14, weight="bold"))
		self.video_info_label.grid(row=1, column=0, columnspan=2, padx=20, pady=(0, 10), sticky="w")

		# Main content: thumbnail (left), options (right)
		main_content_area_frame = ctk.CTkFrame(self, fg_color="#2b2b2b", corner_radius=8)
		main_content_area_frame.grid(row=2, column=0, columnspan=2, padx=20, pady=(0, 10), sticky="nsew")
		main_content_area_frame.grid_rowconfigure(0, weight=1)
		main_content_area_frame.grid_columnconfigure(0, weight=1)
		main_content_area_frame.grid_columnconfigure(1, weight=1)
		# Thumbnail frame (left)
		thumbnail_width = 400
		thumbnail_height = 225
		self.thumbnail_frame = ctk.CTkFrame(main_content_area_frame, fg_color="black", corner_radius=8, width=thumbnail_width, height=thumbnail_height)
		self.thumbnail_frame.grid(row=0, column=0, padx=(15, 10), pady=15, sticky="nsew")
		self.thumbnail_frame.grid_propagate(False)
		self.thumbnail_frame.grid_rowconfigure(0, weight=1)
		self.thumbnail_frame.grid_columnconfigure(0, weight=1)
		self.thumbnail_label = ctk.CTkLabel(self.thumbnail_frame, text="", image=None, fg_color="black", corner_radius=6)
		self.thumbnail_label.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
		# Options group (right)
		options_group_frame = ctk.CTkFrame(main_content_area_frame, fg_color="transparent")
		options_group_frame.grid(row=0, column=1, padx=(5, 15), pady=15, sticky="nsew")
		options_group_frame.grid_columnconfigure(1, weight=1)
		# --- Format, quality, audio, output name, etc. ---
		self.selected_format = ctk.StringVar(value="mp4")
		self.selected_codec = "avc1"
		def set_format(fmt, codec=None):
			self.selected_format.set(fmt)
			self.selected_codec = codec
			for btn, val in zip(self.format_buttons, ["mp3", "webm", "mp4"]):
				if self.selected_format.get() == val:
					btn.configure(fg_color="#1f6aa5")
				else:
					btn.configure(fg_color="#444444")
			if fmt == "mp3":
				self.quality_label.configure(text="Bitrate")
				self.quality_label.grid(row=4, column=0, sticky="w", padx=(10, 5), pady=(0, 0))
				self.quality_menu.grid_remove()
				self.audio_quality_menu.grid(row=5, column=0, padx=(10, 5), pady=(0, 10), sticky="ew")
			else:
				self.quality_label.configure(text="Resolution")
				self.quality_label.grid(row=4, column=0, sticky="w", padx=(10, 5), pady=(0, 0))
				self.audio_quality_menu.grid_remove()
				self.quality_menu.grid(row=5, column=0, padx=(10, 5), pady=(0, 10), sticky="ew")
		self.format_buttons = []
		btn_audio = ctk.CTkButton(options_group_frame, text="Audio/MP3", width=160, height=32,
								  fg_color="#1f6aa5", hover_color="#2a8cdb",
								  font=ctk.CTkFont(size=13, weight="bold"),
								  command=lambda: set_format("mp3", None))
		btn_audio.grid(row=1, column=0, padx=(10, 5), pady=(0, 5), sticky="ew")
		self.format_buttons.append(btn_audio)
		btn_webm = ctk.CTkButton(options_group_frame, text="Video/Webm (vp09)", width=160, height=32,
								 fg_color="#444444", hover_color="#2a8cdb",
								 font=ctk.CTkFont(size=13, weight="bold"),
								 command=lambda: set_format("webm", "vp09"))
		btn_webm.grid(row=2, column=0, padx=(10, 5), pady=(0, 5), sticky="ew")
		self.format_buttons.append(btn_webm)
		btn_mp4 = ctk.CTkButton(options_group_frame, text="Video/MP4 (avc1)", width=160, height=32,
								fg_color="#444444", hover_color="#2a8cdb",
								font=ctk.CTkFont(size=13, weight="bold"),
								command=lambda: set_format("mp4", "avc1"))
		btn_mp4.grid(row=3, column=0, padx=(10, 5), pady=(0, 5), sticky="ew")
		self.format_buttons.append(btn_mp4)
		self.quality_label = ctk.CTkLabel(options_group_frame, text="Resolution", font=ctk.CTkFont(size=13, weight="bold"))
		self.quality_label.grid(row=4, column=0, sticky="w", padx=(10, 5), pady=(0, 0))
		self.quality_var = ctk.StringVar(value="720")
		self.quality_menu = ctk.CTkOptionMenu(options_group_frame, variable=self.quality_var,
											values=["360", "480", "720", "1080", "1440", "2160"],
											fg_color="#1f6aa5", button_hover_color="#2a8cdb",
											font=ctk.CTkFont(size=13, weight="bold"))
		self.quality_menu.grid(row=5, column=0, padx=(10, 5), pady=(0, 10), sticky="ew")
		self.audio_quality_var = ctk.StringVar(value="256k")
		self.audio_quality_menu = ctk.CTkOptionMenu(options_group_frame, variable=self.audio_quality_var,
												  values=["128k", "192k", "256k", "320k"],
												  fg_color="#1f6aa5", button_hover_color="#2a8cdb",
												  font=ctk.CTkFont(size=13, weight="bold"))
		self.audio_quality_menu.grid_remove()
		set_format("mp4", "avc1")
		# Output name
		ctk.CTkLabel(options_group_frame, text="Output Name:", font=ctk.CTkFont(size=12, weight="bold")).grid(row=6, column=0, padx=10, pady=(0, 5), sticky="w")
		self.output_name_var = ctk.StringVar(value="")
		ctk.CTkEntry(options_group_frame, textvariable=self.output_name_var, width=200, font=ctk.CTkFont(size=12, weight="bold")).grid(row=7, column=0, padx=10, pady=(0, 10), sticky="w")

		# Download path section
		download_path_frame = ctk.CTkFrame(self, fg_color="#2b2b2b", corner_radius=8)
		download_path_frame.grid(row=3, column=0, columnspan=2, padx=20, pady=(0, 10), sticky="ew")
		download_path_frame.grid_columnconfigure(0, weight=1)
		self.path_entry = ctk.CTkEntry(download_path_frame, width=400, font=ctk.CTkFont(size=12, weight="bold"))
		self.path_entry.grid(row=0, column=1, padx=(0, 10), pady=10, sticky="w")
		self.path_entry.insert(0, self.download_dir)
		ctk.CTkButton(download_path_frame,image=emoji_("📂", size=22),text="Browse", command=self.browse_dir, font=ctk.CTkFont(size=12, weight="bold")).grid(row=0, column=2, padx=(0, 10), pady=10, sticky="w")
		ctk.CTkButton(download_path_frame, text="Open", command=self.open_dir, font=ctk.CTkFont(size=12, weight="bold"), width=80, height=30).grid(row=0, column=3, padx=(0, 10), pady=10, sticky="w")

		# Fragment options section (will be updated in next step)
		self.fragment_frame = ctk.CTkFrame(self, fg_color="#2b2b2b", corner_radius=8)
		self.fragment_frame.grid(row=4, column=0, columnspan=2, padx=20, pady=(0, 10), sticky="ew")
		self.fragment_frame.grid_columnconfigure(0, weight=0)
		self.fragment_frame.grid_columnconfigure(1, weight=1)
		self.fragment_check = ctk.CTkCheckBox(self.fragment_frame, text="Download specific fragment", variable=self.fragment_enabled, command=self.toggle_fragment_options, font=ctk.CTkFont(size=13, weight="bold"), fg_color="#1f6aa5")
		self.fragment_check.grid(row=0, column=0, padx=15, pady=(10,5), sticky="w")
		self.fragment_time_frame = ctk.CTkFrame(self.fragment_frame, fg_color="transparent")
		self.fragment_time_frame.grid(row=0, column=1, padx=5, pady=(10,5), sticky="w")
		self.fragment_time_frame.grid_columnconfigure(0, weight=0)
		self.fragment_time_frame.grid_columnconfigure(1, weight=0)
		self.fragment_time_frame.grid_columnconfigure(2, weight=0)
		self.fragment_time_frame.grid_columnconfigure(3, weight=0)
		ctk.CTkLabel(self.fragment_time_frame, text="Start:", font=ctk.CTkFont(size=12, weight="bold")).grid(row=0, column=0, sticky="w")
		self.start_time_entry = ctk.CTkEntry(self.fragment_time_frame, textvariable=self.start_time_var, width=90, placeholder_text="hh:mm:ss", font=ctk.CTkFont(size=12, weight="bold"))
		self.start_time_entry.grid(row=0, column=1, padx=(5, 10), sticky="w")
		ctk.CTkLabel(self.fragment_time_frame, text="End:", font=ctk.CTkFont(size=12, weight="bold")).grid(row=0, column=2, sticky="w")
		self.end_time_entry = ctk.CTkEntry(self.fragment_time_frame, textvariable=self.end_time_var, width=90, placeholder_text="hh:mm:ss", font=ctk.CTkFont(size=12, weight="bold"))
		self.end_time_entry.grid(row=0, column=3, padx=(5, 0), sticky="w")
		self.fragment_time_frame.grid_remove()
		self.toggle_fragment_options()

		# Download button and progress
		controls_frame = ctk.CTkFrame(self, fg_color="transparent")
		controls_frame.grid(row=5, column=0, columnspan=2, padx=20, pady=(10, 0), sticky="ew")
		controls_frame.grid_columnconfigure(0, weight=1)
		self.download_button = ctk.CTkButton(controls_frame,image=emoji_("📥", size=28),text="Download", command=self.start_download_thread, fg_color="#1f6aa5", hover_color="#2a8cdb", font=ctk.CTkFont(size=16, weight="bold"))
		self.download_button.grid(row=0, column=0, sticky="ew", pady=(0, 30))
		self.progress_bar = ctk.CTkProgressBar(controls_frame, variable=self.progress_var)
		self.progress_bar.grid(row=1, column=0, sticky="ew")
		self.progress_bar.grid_remove()
		self.progress_label = ctk.CTkLabel(self, textvariable=self.status_var, anchor="center", font=ctk.CTkFont(size=12, weight="bold"))
		self.progress_label.grid(row=6, column=0, columnspan=2, pady=(0, 20))
		self.progress_label.grid_remove()
	def update_available_resolutions(self, max_resolution):
		available_resolutions = ["360", "480", "720", "1080", "1440", "2160"]
		filtered_resolutions = [res for res in available_resolutions if int(res) <= int(max_resolution)]
		self.quality_menu.configure(values=filtered_resolutions)
		if self.quality_var.get() not in filtered_resolutions:
			self.quality_var.set(filtered_resolutions[-1])
	def start_search_thread(self):
		threading.Thread(target=self.search_video, daemon=True).start()
	def browse_dir(self):
		folder = filedialog.askdirectory(initialdir=self.download_dir, title="Select Download Directory")
		if folder:
			self.download_dir = folder
			self.path_entry.delete(0, "end")
			self.path_entry.insert(0, folder)

	def toggle_fragment_options(self):
		if self.fragment_enabled.get():
			self.fragment_time_frame.grid()
		else:
			self.fragment_time_frame.grid_remove()

	def open_dir(self):
		"""Open the configured download directory in the system file explorer."""
		path = self.path_entry.get().strip()
		if not path:
			return
		if not os.path.exists(path):
			messagebox.showwarning("Not found", f"Folder does not exist: {path}")
			return
		try:
			if sys.platform == 'win32':
				os.startfile(path)
			else:
				# cross-platform fallback
				subprocess.run(['xdg-open' if sys.platform == 'linux' else 'open', path], check=False)
		except Exception as e:
			messagebox.showerror("Error", f"Could not open folder: {e}")

	def search_video(self):
		url = self.url_var.get().strip()
		if not url:
			messagebox.showwarning("Input Required", "Please enter a video URL or name.")
			return
		libs_dir = get_libs_dir()
		yt_dlp_path = os.path.join(libs_dir, 'yt-dlp.exe')
		if not os.path.exists(yt_dlp_path):
			self.video_info_label.configure(text=f"yt-dlp.exe not found in {libs_dir}")
			return
		# If not a URL, use ytsearch1:
		is_search = not (url.startswith('http://') or url.startswith('https://'))
		if is_search:
			search_term = f"ytsearch1:{url}"
		else:
			search_term = url
		cmd = [yt_dlp_path, '--no-warnings', '--dump-json', search_term]
		env = os.environ.copy()
		env['PATH'] = libs_dir + os.pathsep + env.get('PATH', '')
		try:
			creationflags = 0
			if os.name == 'nt':
				creationflags = subprocess.CREATE_NO_WINDOW
			proc = subprocess.run(cmd, capture_output=True, text=True, env=env, creationflags=creationflags, timeout=20)
			if proc.returncode == 0:
				import json
				try:
					out = proc.stdout.strip().split('\n')[0]
					info = json.loads(out)
					if 'entries' in info and info['entries']:
						info = info['entries'][0]
					title = info.get('title', 'Unknown')
					duration = info.get('duration', 0)
					thumbnail = info.get('thumbnail', None)
					views = info.get('view_count', None)
					likes = info.get('like_count', None)
					webpage_url = info.get('webpage_url', url)
					self.resolved_video_url = webpage_url
					max_height = 0
					for f in info.get('formats', []):
						if f.get('height'):
							max_height = max(max_height, f.get('height'))
					self.update_available_resolutions(max_height)
					
					# Format duration as HH:MM:SS
					def format_duration(seconds):
						try:
							seconds = int(seconds)
							h = seconds // 3600
							m = (seconds % 3600) // 60
							s = seconds % 60
							return f"{h:02}:{m:02}:{s:02}"
						except:
							return str(seconds)
					duration_str = format_duration(duration)
					info_text = f"Title: {title}\nDuration: {duration_str}"
					if views is not None:
						info_text += f"\nViews: {views:,}"
					if likes is not None:
						info_text += f"\nLikes: {likes:,}"
					self.video_info_label.configure(text=info_text)
					if thumbnail:
						self.show_thumbnail(thumbnail)
				except Exception as e:
					self.video_info_label.configure(text=f"Could not parse video info: {e}")
			else:
				self.video_info_label.configure(text=f"No video found or error.")
		except Exception as e:
			self.video_info_label.configure(text=f"Error: {e}")

	def show_thumbnail(self, url):
		try:
			import requests
			from PIL import Image
			from io import BytesIO
			resp = requests.get(url, timeout=10)
			img = Image.open(BytesIO(resp.content))
			# Fit to 400x225 (16:9) while preserving aspect ratio
			def fit_image_to_aspect_ratio(image, target_width, target_height):
				aspect = target_width / target_height
				img_w, img_h = image.size
				img_aspect = img_w / img_h
				if img_aspect > aspect:
					new_w = target_width
					new_h = int(target_width / img_aspect)
				else:
					new_h = target_height
					new_w = int(target_height * img_aspect)
				return image.resize((new_w, new_h), Image.LANCZOS)
			fitted = fit_image_to_aspect_ratio(img, 400, 225)
			from customtkinter import CTkImage
			self.thumbnail_img = CTkImage(light_image=fitted, dark_image=fitted, size=(fitted.width, fitted.height))
			self.thumbnail_label.configure(image=self.thumbnail_img)
		except Exception:
			self.thumbnail_label.configure(image=None)
			pass

	def start_download_thread(self):
		url = self.url_var.get().strip()
		if not url:
			messagebox.showwarning("Input Required", "Please enter a video URL.")
			return
		out_dir = self.path_entry.get().strip()
		if not os.path.exists(out_dir):
			os.makedirs(out_dir)
		self.status_var.set("Starting download...")
		self.geometry("700x680")
		self.progress_var.set(0.0)
		self.progress_bar.grid()  # Ensure progress bar is visible
		self.progress_label.grid()  # Ensure label is visible
		# Use resolved_video_url if available (from search)
		download_url = self.resolved_video_url if self.resolved_video_url else url
		threading.Thread(target=self.download_video, args=(download_url, out_dir), daemon=True).start()

	def download_video(self, url, out_dir):
		libs_dir = get_libs_dir()
		yt_dlp_path = os.path.join(libs_dir, 'yt-dlp.exe')
		ffmpeg_path = os.path.join(libs_dir, 'ffmpeg.exe')
		if not os.path.exists(yt_dlp_path):
			self.status_var.set(f"yt-dlp.exe not found in {libs_dir}")
			return
		# Check for ffmpeg in libs, else in PATH
		if os.path.exists(ffmpeg_path):
			ffmpeg_to_use = ffmpeg_path
		else:
			ffmpeg_in_path = shutil.which('ffmpeg')
			if ffmpeg_in_path:
				ffmpeg_to_use = ffmpeg_in_path
			else:
				self.status_var.set("ffmpeg.exe not found in libs or PATH")
				return
		# Compose yt-dlp command
		output_name = self.output_name_var.get().strip() or '%(title)s'
		output_template = os.path.join(out_dir, sanitize_filename(output_name) + '.%(ext)s')
		cmd = [yt_dlp_path, url, '-o', output_template, '--ffmpeg-location', ffmpeg_to_use, '--progress-template', '%(progress._percent_str)s']
		# Format/quality/audio
		if self.selected_format.get() == 'mp3':
			cmd += ['-x', '--audio-format', 'mp3', '--audio-quality', self.audio_quality_var.get()]
		else:
			if self.quality_var.get() != 'best':
				cmd += ['-f', f'bestvideo[height<={self.quality_var.get()}]+bestaudio/best[height<={self.quality_var.get()}]']
		# Fragment
		if self.fragment_enabled.get():
			start = self.start_time_var.get()
			end = self.end_time_var.get()
			if start and end and start != "00:00:00" and end != "00:00:00":
				cmd += ['--force-keyframes-at-cuts', '--download-sections', f'*{start}-{end}']
		env = os.environ.copy()
		env['PATH'] = libs_dir + os.pathsep + env.get('PATH', '')
		self.status_var.set("Downloading...")
		try:
			creationflags = 0
			if os.name == 'nt':
				creationflags = subprocess.CREATE_NO_WINDOW
			process = subprocess.Popen(
				cmd,
				stdout=subprocess.PIPE,
				stderr=subprocess.STDOUT,
				env=env,
				text=True,
				bufsize=1,
				creationflags=creationflags
			)
			for line in process.stdout:
				self.parse_progress(line)
			process.wait()
			if process.returncode == 0:
				self.status_var.set("Download complete!")
				self.progress_var.set(1.0)
				# self.progress_bar.set(1)  # Removed to prevent double updates
			else:
				self.status_var.set("Download failed.")
		except Exception as e:
			self.status_var.set(f"Error: {e}")

	def parse_progress(self, line):
		# Only update bar for main download, not merging/extracting/post-process
		stage_keywords = ["Merging", "Extracting", "Post-process", "delete", "move", "ffmpeg", "Writing"]
		for kw in stage_keywords:
			if kw.lower() in line.lower():
				# Show current stage and reset bar
				self.status_var.set(f"{kw}...")
				self.progress_var.set(0.0)
				self.progress_bar.grid()
				self.progress_label.grid()
				return
		prog = re.search(r'(\d{1,3}\.\d)%', line)
		if prog:
			percent = float(prog.group(1))
			last = self.progress_var.get()
			if percent > last * 100:
				self.progress_var.set(percent / 100)
			self.status_var.set(f"Downloading... {percent:.1f}%")
		# Always ensure progress bar and label are visible during download
		self.progress_bar.grid()
		self.progress_label.grid()
	def setup_right_click_menu(self):
		import tkinter as tk
		self.right_click_menu = tk.Menu(self.url_entry, tearoff=0)
		self.right_click_menu.add_command(label="Paste", command=self.paste_url)
		self.right_click_menu.add_command(label="Cut", command=self.cut_url)
		def show_menu(event):
			self.right_click_menu.tk_popup(event.x_root, event.y_root)
		self.url_entry.bind("<Button-3>", show_menu)

	def paste_url(self):
		try:
			text = self.clipboard_get()
			self.url_entry.delete(0, "end")
			self.url_entry.insert(0, text)
			self.url_var.set(text)
		except Exception:
			pass

	def cut_url(self):
		try:
			text = self.url_entry.get()
			self.clipboard_clear()
			self.clipboard_append(text)
			self.url_entry.delete(0, "end")
			self.url_var.set("")
		except Exception:
			pass

def main():
	app = DownloaderApp()
	app.mainloop()

if __name__ == "__main__":
	main()