
import os
import requests
import shutil
import tempfile
import hashlib

YT_DLP_URL = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
MAIN_PROGRAM_URL = "https://github.com/suskese/Video-Downloader/releases/latest/download/Video Downloader.exe"

import sys
def resource_path(relative):
	if hasattr(sys, '_MEIPASS'):
		return os.path.join(sys._MEIPASS, relative)
	return os.path.join(os.path.dirname(__file__), relative)

LIBS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'libs'))
if hasattr(sys, '_MEIPASS'):
	# If bundled, libs is next to the exe
	base_dir = os.path.dirname(sys.executable)
	LIBS_DIR = os.path.join(base_dir, 'libs')
YT_DLP_PATH = os.path.join(LIBS_DIR, 'yt-dlp.exe')
MAIN_PROGRAM_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'Video Downloader.exe'))
if hasattr(sys, '_MEIPASS'):
	MAIN_PROGRAM_PATH = os.path.join(os.path.dirname(sys.executable), 'Video Downloader.exe')

def file_hash(path):
	if not os.path.exists(path):
		return None
	h = hashlib.sha256()
	with open(path, 'rb') as f:
		while True:
			chunk = f.read(8192)
			if not chunk:
				break
			h.update(chunk)
	return h.hexdigest()

def download_file(url, dest):
	with requests.get(url, stream=True) as r:
		r.raise_for_status()
		with open(dest, 'wb') as f:
			for chunk in r.iter_content(chunk_size=8192):
				f.write(chunk)

def update_yt_dlp():
	print("Checking yt-dlp.exe for updates...")
	with tempfile.NamedTemporaryFile(delete=False) as tmp:
		tmp_path = tmp.name
	try:
		download_file(YT_DLP_URL, tmp_path)
		if file_hash(tmp_path) != file_hash(YT_DLP_PATH):
			shutil.move(tmp_path, YT_DLP_PATH)
			print("yt-dlp.exe updated.")
		else:
			print("yt-dlp.exe is up to date.")
			os.remove(tmp_path)
	except Exception as e:
		print(f"Failed to update yt-dlp.exe: {e}")
		if os.path.exists(tmp_path):
			os.remove(tmp_path)

def update_main_program():
	print("Checking main program for updates...")
	with tempfile.NamedTemporaryFile(delete=False) as tmp:
		tmp_path = tmp.name
	try:
		download_file(MAIN_PROGRAM_URL, tmp_path)
		if file_hash(tmp_path) != file_hash(MAIN_PROGRAM_PATH):
			shutil.move(tmp_path, MAIN_PROGRAM_PATH)
			print("Main program updated.")
		else:
			print("Main program is up to date.")
			os.remove(tmp_path)
	except Exception as e:
		print(f"Failed to update main program: {e}")
		if os.path.exists(tmp_path):
			os.remove(tmp_path)

if __name__ == "__main__":
	update_yt_dlp()
	update_main_program()