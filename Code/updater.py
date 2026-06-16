import os
import sys
import json
import urllib.request
import subprocess
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtWidgets import QMessageBox, QProgressDialog, QApplication

APP_VERSION = "1.0.1"
GITHUB_REPO = "DPSSCOPY/Photo-Print-App"

class UpdateCheckerThread(QThread):
    update_available = pyqtSignal(str, str, str) # version, release_notes, download_url
    no_update = pyqtSignal()
    error_occurred = pyqtSignal(str)

    def run(self):
        try:
            url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
                
                latest_version = data.get('tag_name', '').lower().lstrip('v')
                release_notes = data.get('body', '')
                
                # Compare versions (simple string comparison for semantic versioning)
                # Assumes version format like "1.0.0"
                if self.is_newer_version(APP_VERSION, latest_version):
                    # Look for .zip first, then .exe
                    download_url = None
                    is_zip = False
                    for asset in data.get('assets', []):
                        name = asset.get('name', '').lower()
                        if name.endswith('.zip'):
                            download_url = asset.get('browser_download_url')
                            is_zip = True
                            break
                        elif name.endswith('.exe') and not download_url:
                            download_url = asset.get('browser_download_url')
                    
                    if download_url:
                        self.update_available.emit(latest_version, release_notes, f"{download_url}|{'zip' if is_zip else 'exe'}")
                    else:
                        self.no_update.emit()
                else:
                    self.no_update.emit()
        except Exception as e:
            self.error_occurred.emit(str(e))

    def is_newer_version(self, current, latest):
        def parse_version(v):
            return [int(x) for x in v.lower().replace('v', '').split('.') if x.isdigit()]
        try:
            return parse_version(latest) > parse_version(current)
        except:
            return latest != current and latest != ""

class UpdateDownloader(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, download_url, save_path):
        super().__init__()
        self.download_url = download_url
        self.save_path = save_path

    def run(self):
        try:
            req = urllib.request.Request(self.download_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=15) as response:
                total_size = int(response.info().get('Content-Length', 0))
                downloaded = 0
                block_size = 8192
                
                with open(self.save_path, 'wb') as file:
                    while True:
                        buffer = response.read(block_size)
                        if not buffer:
                            break
                        file.write(buffer)
                        downloaded += len(buffer)
                        if total_size > 0:
                            percent = int(downloaded * 100 / total_size)
                            self.progress.emit(percent)
                            
            self.finished.emit(self.save_path)
        except Exception as e:
            self.error.emit(str(e))

def check_for_updates(parent_widget):
    checker = UpdateCheckerThread(parent_widget)
    
    def on_update_available(version, notes, url_info):
        url, file_type = url_info.split('|')
        msg = QMessageBox(parent_widget)
        msg.setWindowTitle("កំណែថ្មី / Update Available")
        msg.setText(f"កម្មវិធីមានកំណែថ្មី <b>v{version}</b>។<br>តើអ្នកចង់ទាញយក និងអាប់ដេតឥឡូវនេះទេ?")
        msg.setDetailedText(notes)
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.Yes)
        
        if msg.exec_() == QMessageBox.Yes:
            download_update(parent_widget, url, version, file_type)
            
    checker.update_available.connect(on_update_available)
    checker.start()
    parent_widget._update_checker = checker

def download_update(parent_widget, url, version, file_type):
    if not sys.argv[0].endswith('.exe'):
        QMessageBox.warning(parent_widget, "ចំណាំ / Notice", "មុខងារ Auto-Update អាចប្រើបានតែនៅពេលអ្នកដំណើរការជាឯកសារ .exe ប៉ុណ្ណោះ។\n(បច្ចុប្បន្នអ្នកកំពុងដំណើរការជាកូដ Python)")
        return

    progress_dialog = QProgressDialog("កំពុងទាញយកឯកសារកំណែថ្មី...\nសូមរង់ចាំបន្តិច!", "បោះបង់", 0, 100, parent_widget)
    progress_dialog.setWindowTitle("កំពុងទាញយក / Downloading")
    progress_dialog.setWindowModality(Qt.WindowModal)
    progress_dialog.setAutoClose(True)
    progress_dialog.setMinimumDuration(0)
    progress_dialog.setValue(0)
    
    current_exe = sys.argv[0]
    
    if file_type == 'zip':
        new_file_path = os.path.join(os.path.dirname(current_exe), "update.zip")
    else:
        new_file_path = current_exe + ".new"
    
    downloader = UpdateDownloader(url, new_file_path)
    downloader.progress.connect(progress_dialog.setValue)
    
    def on_download_finished(saved_path):
        progress_dialog.setValue(100)
        apply_update(current_exe, saved_path, file_type)
        
    def on_download_error(err):
        progress_dialog.cancel()
        QMessageBox.critical(parent_widget, "បរាជ័យ / Error", f"មានបញ្ហាក្នុងការទាញយក៖ {err}")
        
    progress_dialog.canceled.connect(downloader.terminate)
    downloader.finished.connect(on_download_finished)
    downloader.error.connect(on_download_error)
    
    downloader.start()
    parent_widget._update_downloader = downloader

def apply_update(current_exe, downloaded_file, file_type):
    bat_path = os.path.join(os.path.dirname(current_exe), "update.bat")
    current_dir = os.path.dirname(current_exe)
    exe_name = os.path.basename(current_exe)
    
    if file_type == 'zip':
        # Script for replacing an entire folder structure (Pyinstaller --onedir)
        bat_content = f"""@echo off
echo Updating Photo Print App... Please wait.
timeout /t 3 /nobreak > NUL

rmdir /s /q "_internal"
del "{exe_name}"

powershell -command "Expand-Archive -Path 'update.zip' -DestinationPath '.' -Force"

del "update.zip"
start "" "{exe_name}"
del "%~f0"
"""
    else:
        # Script for a single .exe replacement
        bat_content = f"""@echo off
echo Updating Photo Print App... Please wait.
timeout /t 2 /nobreak > NUL
del "{exe_name}"
if exist "{exe_name}" (
    echo Failed to delete the old version. Please close the app and try again.
    pause
    exit
)
ren "{os.path.basename(downloaded_file)}" "{exe_name}"
start "" "{exe_name}"
del "%~f0"
"""
    
    try:
        with open(bat_path, "w", encoding="utf-8") as f:
            f.write(bat_content)
        
        subprocess.Popen([bat_path], shell=True, cwd=current_dir)
        
        QApplication.quit()
        sys.exit()
    except Exception as e:
        QMessageBox.critical(None, "បរាជ័យ / Error", f"មានបញ្ហាក្នុងការដំឡើងកំណែថ្មី៖ {e}")
