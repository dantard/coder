import io
import os
import sys
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QListWidget, QListWidgetItem,
    QLineEdit, QProgressDialog, QFileDialog, QMessageBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import json
import base64

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
MY_FOLDER_ID = "134HW0zwAkEGWG1S8qD122BAtsTbLcOlS"

cs = ("eyJpbnN0YWxsZWQiOnsiY2xpZW50X2lkIjoiOTIxNDI4Mjc"
      "1Ni1pZHJybDYyOGIwc2JzcWtxcWRnM3ByYW9rNHA5NXU4YS5"
      "hcHBzLmdvb2dsZXVzZXJjb250ZW50LmNvbSIsInByb2plY3R"
      "faWQiOiJwcm9qZWN0LTZmYWQ3NjRiLTdkZDQtNDZiMS1hNjM"
      "iLCJhdXRoX3VyaSI6Imh0dHBzOi8vYWNjb3VudHMuZ29vZ2x"
      "lLmNvbS9vL29hdXRoMi9hdXRoIiwidG9rZW5fdXJpIjoiaHR"
      "0cHM6Ly9vYXV0aDIuZ29vZ2xlYXBpcy5jb20vdG9rZW4iLCJ"
      "hdXRoX3Byb3ZpZGVyX3g1MDlfY2VydF91cmwiOiJodHRwczo"
      "vL3d3dy5nb29nbGVhcGlzLmNvbS9vYXV0aDIvdjEvY2VydHM"
      "iLCJjbGllbnRfc2VjcmV0IjoiR09DU1BYLWdZYVdWSUJpbkN"
      "0T1ZoS3ZaazhDTjB1a1NwODMiLCJyZWRpcmVjdF91cmlzIjp"
      "bImh0dHA6Ly9sb2NhbGhvc3QiXX19")


# ── Auth & Drive ────────────────────────────────────────────────────────────

def get_gdrive_service(encoded_secret: str):
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            client_secrets_str = base64.b64decode(encoded_secret).decode()
            client_config = json.loads(client_secrets_str)
            flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('drive', 'v3', credentials=creds)

# def get_gdrive_service():
#     creds = None
#     if os.path.exists('token.json'):
#         creds = Credentials.from_authorized_user_file('token.json', SCOPES)
#     if not creds or not creds.valid:
#         if creds and creds.expired and creds.refresh_token:
#             creds.refresh(Request())
#         else:
#             flow = InstalledAppFlow.from_client_secrets_file('client_secrets.json', SCOPES)
#             creds = flow.run_local_server(port=0)
#         with open('token.json', 'w') as token:
#             token.write(creds.to_json())
#     return build('drive', 'v3', credentials=creds)


# ── Workers ─────────────────────────────────────────────────────────────────

class FetchFilesWorker(QThread):
    files_ready = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, folder_id):
        super().__init__()
        self.folder_id = folder_id

    def run(self):
        try:
            service = get_gdrive_service(cs)
            query = (
                f"'{self.folder_id}' in parents "
                "and mimeType = 'application/vnd.google-apps.presentation' "
                "and trashed = false"
            )
            results = service.files().list(q=query, fields="files(id, name)").execute()
            self.files_ready.emit(results.get('files', []))
        except Exception as e:
            self.error.emit(str(e))


class DownloadWorker(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, file_id, file_name, save_path):
        super().__init__()
        self.file_id = file_id
        self.file_name = file_name
        self.save_path = save_path

    def run(self):
        try:
            service = get_gdrive_service(cs)
            request = service.files().export_media(
                fileId=self.file_id,
                mimeType='application/pdf'
            )
            with io.FileIO(self.save_path, 'wb') as fh:
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
                    self.progress.emit(int(status.progress() * 100))
            self.finished.emit(self.save_path)
        except Exception as e:
            self.error.emit(str(e))


# ── Widget ───────────────────────────────────────────────────────────────────

class DrivePdfDownloaderWidget(QWidget):

    done = pyqtSignal(str)  # Emits the path of the downloaded PDF

    def __init__(self, folder_id=MY_FOLDER_ID, save_path=None, parent=None):
        super().__init__(parent)
        self.folder_id = folder_id
        self.save_path = save_path
        self.files = []
        self.fetch_worker = None
        self.download_worker = None
        self._build_ui()
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Folder ID row
        folder_row = QHBoxLayout()
        folder_row.addWidget(QLabel("Folder ID:"))
        self.folder_input = QLineEdit(self.folder_id)
        folder_row.addWidget(self.folder_input)
        self.load_btn = QPushButton("Load")
        self.load_btn.clicked.connect(self._on_load_clicked)
        if self.folder_id is None:
            self.folder_input.setPlaceholderText("Paste Google Drive folder ID…")
            folder_row.addWidget(self.load_btn)
        else:
            self.folder_input.setReadOnly(True)

        layout.addLayout(folder_row)

        # Top row: status label + refresh button
        top_row = QHBoxLayout()
        self.status_label = QLabel("Enter a folder ID and click Load.")
        top_row.addWidget(self.status_label)
        top_row.addStretch()
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.clicked.connect(self._load_files)
        top_row.addWidget(self.refresh_btn)
        layout.addLayout(top_row)

        # File list
        self.file_list = QListWidget()
        self.file_list.itemClicked.connect(self._on_item_selected)
        self.file_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.file_list)

        # Download button
        self.download_btn = QPushButton("Download as PDF")
        self.download_btn.setEnabled(False)
        self.download_btn.clicked.connect(self._on_download_clicked)
        #layout.addWidget(self.download_btn)

        if self.folder_id:
            self._load_files()

    # ── File loading ──────────────────────────────────────────────────────

    def _on_load_clicked(self):
        folder_id = self.folder_input.text().strip()
        if not folder_id:
            QMessageBox.warning(self, "Missing Folder ID", "Please enter a Google Drive folder ID.")
            return
        self.folder_id = folder_id
        self._load_files()

    def _load_files(self):
        self.file_list.clear()
        self.files = []
        self.download_btn.setEnabled(False)
        self.refresh_btn.setEnabled(False)
        self.load_btn.setEnabled(False)
        self.status_label.setText("Fetching files…")

        self.fetch_worker = FetchFilesWorker(self.folder_id)
        self.fetch_worker.files_ready.connect(self._on_files_ready)
        self.fetch_worker.error.connect(self._on_fetch_error)
        self.fetch_worker.start()

    def _on_files_ready(self, files):
        self.files = files
        self.refresh_btn.setEnabled(True)
        self.load_btn.setEnabled(True)
        if not files:
            self.status_label.setText("No presentations found.")
            return
        noun = "presentation" if len(files) == 1 else "presentations"
        self.status_label.setText(f"{len(files)} {noun} found")
        files.sort(key=lambda f: f['name'].lower())
        for f in files:
            item = QListWidgetItem(f['name'])
            item.setData(Qt.UserRole, f)
            self.file_list.addItem(item)

        w = self.file_list.sizeHintForColumn(0) + 2 * self.file_list.frameWidth()
        self.file_list.setMinimumWidth(w+30)

    def _on_fetch_error(self, msg):
        self.refresh_btn.setEnabled(True)
        self.load_btn.setEnabled(True)
        self.status_label.setText("Error fetching files.")
        QMessageBox.critical(self, "Connection Error", msg)

    # ── Selection ─────────────────────────────────────────────────────────

    def _on_item_selected(self, item):
        self.download_btn.setEnabled(True)

    def _on_item_double_clicked(self, item):
        self._start_download(item.data(Qt.UserRole))

    # ── Download ──────────────────────────────────────────────────────────

    def _on_download_clicked(self):
        item = self.file_list.currentItem()
        if item:
            self._start_download(item.data(Qt.UserRole))

    def _start_download(self, file_info):
        if self.save_path is None:
            self.save_path = QFileDialog.getExistingDirectory(
                self, "Select Download Folder", os.path.expanduser("~")
            )
        if not self.save_path:
            return
        file_name = file_info['name']
        self.download_btn.setEnabled(False)
        self.status_label.setText(f"Exporting '{file_name}'…")

        self.progress_dialog = QProgressDialog(
            f"Exporting '{file_name}'…", "Cancel", 0, 100, self
        )
        self.progress_dialog.setWindowTitle("Downloading PDF")
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.setMinimumDuration(0)
        self.progress_dialog.setValue(0)

        self.download_worker = DownloadWorker(file_info['id'], file_info['name'], self.save_path + os.sep + file_info['name'] + ".pdf")
        self.download_worker.progress.connect(self.progress_dialog.setValue)
        self.download_worker.finished.connect(self._on_finished)
        self.download_worker.error.connect(self._on_download_error)
        self.progress_dialog.canceled.connect(self.download_worker.terminate)
        self.download_worker.start()

    def _on_finished(self, path):
        self.progress_dialog.setValue(100)
        self.progress_dialog.close()
        self.status_label.setText(f"Saved: {os.path.basename(path)}")
        self.download_btn.setEnabled(True)
        #QMessageBox.information(self, "Done", f"PDF saved to:\n{path}")
        self.done.emit(path)
        self.hide()
        self.deleteLater()

    def _on_download_error(self, msg):
        self.progress_dialog.close()
        self.download_btn.setEnabled(True)
        self.status_label.setText("Export failed.")
        QMessageBox.critical(self, "Download Error", msg)


# ── Minimal runner (for testing the widget standalone) ───────────────────────

if __name__ == "__main__":
    app = QApplication(sys.argv)
    widget = DrivePdfDownloaderWidget()
    widget.setWindowTitle("Drive PDF Downloader")
    widget.resize(500, 400)
    widget.show()
    sys.exit(app.exec_())