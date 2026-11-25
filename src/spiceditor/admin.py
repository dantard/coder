"""
Admin panel for the collaboration server (server.py).

Shows every session and who is connected to it, and lets you mute a client
(the server rejects its edits, its editor turns read-only) or disconnect it.
Needs the admin token the server prints at startup.

Run:  python admin.py --server 127.0.0.1:5000 --token SECRET
"""
import argparse
import json
import sys
from urllib.parse import quote

from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QColor, QIcon, QPixmap
from PyQt5.QtWidgets import (QApplication, QCheckBox, QHBoxLayout, QHeaderView, QLabel,
                             QLineEdit, QMessageBox, QPushButton, QTreeWidget,
                             QTreeWidgetItem, QVBoxLayout, QWidget)

try:
    from spiceditor import webrequest
except ImportError:  # running admin.py directly from its folder
    import webrequest

REFRESH_MS = 2000
COL_NAME, COL_STATUS, COL_SEEN, COL_ACTIONS = range(4)


def _swatch(color):
    pixmap = QPixmap(12, 12)
    pixmap.fill(QColor(color))
    return QIcon(pixmap)


def _buttons(*specs):
    """A row of small buttons: specs are (text, tooltip, callback)."""
    box = QWidget()
    layout = QHBoxLayout(box)
    layout.setContentsMargins(2, 0, 2, 0)
    layout.setSpacing(4)
    buttons = []
    for text, tip, callback in specs:
        b = QPushButton(text)
        b.setToolTip(tip)
        b.clicked.connect(callback)
        layout.addWidget(b)
        buttons.append(b)
    layout.addStretch()
    return box, buttons


class AdminWidget(QWidget):
    def __init__(self, server="127.0.0.1:5000", token="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Spice - collaboration admin")
        self.refresh_reply = None
        self.started = False   # Connect pressed: refresh while the window is shown
        self.sessions = {}     # session -> QTreeWidgetItem
        self.clients = {}      # (session, client_id) -> (item, mute button)
        self.data = {}         # session -> list of client dicts (last refresh)

        self.server_edit = QLineEdit(server)
        self.server_edit.setPlaceholderText("host:port")
        self.token_edit = QLineEdit(token)
        self.token_edit.setEchoMode(QLineEdit.Password)
        self.token_edit.setPlaceholderText("admin token printed by server.py")
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.start)
        self.show_empty = QCheckBox("Show empty sessions")
        self.show_empty.toggled.connect(self.refresh)

        top = QHBoxLayout()
        top.addWidget(QLabel("Server:"))
        top.addWidget(self.server_edit, 2)
        top.addWidget(QLabel("Token:"))
        top.addWidget(self.token_edit, 2)
        top.addWidget(self.connect_button)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Session / user", "Status", "Last seen", ""])
        self.tree.setRootIsDecorated(True)
        self.tree.setSelectionMode(QTreeWidget.NoSelection)
        header = self.tree.header()
        header.setSectionResizeMode(COL_NAME, QHeaderView.Stretch)
        for col in (COL_STATUS, COL_SEEN, COL_ACTIONS):
            header.setSectionResizeMode(col, QHeaderView.ResizeToContents)

        self.status = QLabel("Not connected")

        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self.tree)
        bottom = QHBoxLayout()
        bottom.addWidget(self.status, 1)
        bottom.addWidget(self.show_empty)
        layout.addLayout(bottom)

        self.timer = QTimer(self)
        self.timer.setInterval(REFRESH_MS)
        self.timer.timeout.connect(self.refresh)
        self.resize(720, 420)

    # ------------------------------------------------------------------
    # HTTP
    # ------------------------------------------------------------------
    def _base(self):
        server = self.server_edit.text().strip().rstrip("/")
        return server if "://" in server else "http://" + server

    def _request(self, method, path, payload=None, callback=None):
        headers = {"X-Admin-Token": self.token_edit.text().strip()}

        def finished(ok, status, body):
            try:
                data = json.loads(body) if body else {}
            except ValueError:
                data = {}
            if callback:
                callback(ok, status, data)

        url = self._base() + path
        if method == "GET":
            return webrequest.get(url, finished, headers=headers, timeout=5)
        return webrequest.post(url, payload, finished, headers=headers, timeout=5)

    def _report_error(self, status, data):
        if status == 401:
            self.status.setText("Wrong admin token")
        elif status == 0:
            self.status.setText(f"Cannot reach {self._base()}")
        else:
            self.status.setText(f"Error {status}: {data.get('error', '')}")

    # ------------------------------------------------------------------
    # refreshing the list
    # ------------------------------------------------------------------
    def start(self):
        self.tree.clear()
        self.sessions.clear()
        self.clients.clear()
        self.status.setText("Connecting…")
        self.started = True
        self.timer.start()
        self.refresh()

    def showEvent(self, event):
        super().showEvent(event)
        if self.started and not self.timer.isActive():
            self.timer.start()
            self.refresh()

    def hideEvent(self, event):
        # no polling while the window is closed
        self.timer.stop()
        super().hideEvent(event)

    def refresh(self):
        if not self.timer.isActive() or self.refresh_reply is not None:
            return
        self.refresh_reply = self._request("GET", "/api/admin/clients", callback=self._on_refresh)

    def _on_refresh(self, ok, status, data):
        self.refresh_reply = None
        if not ok:
            self._report_error(status, data)
            return
        sessions = {s["session"]: s for s in data["sessions"]
                    if s["clients"] or self.show_empty.isChecked()}
        self.data = {name: s["clients"] for name, s in sessions.items()}

        # sessions and clients that are gone
        for key in [k for k in self.clients if k[0] not in sessions or
                    k[1] not in {c["client_id"] for c in sessions[k[0]]["clients"]}]:
            item, _ = self.clients.pop(key)
            item.parent().removeChild(item)
        for name in [n for n in self.sessions if n not in sessions]:
            self.tree.takeTopLevelItem(self.tree.indexOfTopLevelItem(self.sessions.pop(name)))

        for name, session in sessions.items():
            self._update_session(name, session)

        users = sum(len(s["clients"]) for s in sessions.values())
        self.status.setText(f"Connected to {self._base()} - {users} user(s) in "
                            f"{sum(1 for s in sessions.values() if s['clients'])} session(s)")

    def _update_session(self, name, session):
        item = self.sessions.get(name)
        if item is None:
            item = QTreeWidgetItem()
            self.tree.addTopLevelItem(item)
            box, _ = _buttons(("Mute all", "Mute everybody in this session",
                               lambda: self.mute_session(name, True)),
                              ("Unmute all", "Unmute everybody in this session",
                               lambda: self.mute_session(name, False)))
            self.tree.setItemWidget(item, COL_ACTIONS, box)
            item.setExpanded(True)
            font = item.font(COL_NAME)
            font.setBold(True)
            item.setFont(COL_NAME, font)
            self.sessions[name] = item
        clients = session["clients"]
        muted = sum(c["muted"] for c in clients)
        item.setText(COL_NAME, f"Session {name}")
        item.setText(COL_STATUS, f"{len(clients)} connected" + (f", {muted} muted" if muted else ""))
        item.setText(COL_SEEN, f"{session['length']} chars")

        for c in clients:
            key = (name, c["client_id"])
            if key not in self.clients:
                child = QTreeWidgetItem(item)
                box, (mute, _) = _buttons(
                    ("Mute", "Mute / unmute: a muted user cannot edit",
                     lambda _=False, k=key: self.toggle_mute(*k)),
                    ("Disconnect", "Disconnect this user from the session",
                     lambda _=False, k=key: self.kick(*k)))
                self.tree.setItemWidget(child, COL_ACTIONS, box)
                self.clients[key] = (child, mute)
            child, mute = self.clients[key]
            child.setText(COL_NAME, c["name"])
            child.setIcon(COL_NAME, _swatch(c["color"]))
            child.setToolTip(COL_NAME, f"client id {c['client_id']}")
            child.setText(COL_STATUS, "Muted" if c["muted"] else "Editing")
            child.setForeground(COL_STATUS, QColor("#c0392b") if c["muted"] else QColor("#27ae60"))
            child.setText(COL_SEEN, "now" if c["seen"] < 3 else f"{int(c['seen'])} s ago")
            mute.setText("Unmute" if c["muted"] else "Mute")

    # ------------------------------------------------------------------
    # actions
    # ------------------------------------------------------------------
    def _client(self, session, client_id):
        return next((c for c in self.data.get(session, []) if c["client_id"] == client_id), None)

    def _after_action(self, ok, status, data):
        if not ok:
            self._report_error(status, data)
        self.refresh()

    def set_muted(self, session, client_id, muted):
        self._request("POST", f"/api/admin/docs/{quote(session, safe='')}/clients/{client_id}/mute",
                      {"muted": muted}, self._after_action)

    def toggle_mute(self, session, client_id):
        client = self._client(session, client_id)
        if client is not None:
            self.set_muted(session, client_id, not client["muted"])

    def mute_session(self, session, muted):
        for c in self.data.get(session, []):
            if c["muted"] != muted:
                self.set_muted(session, c["client_id"], muted)

    def kick(self, session, client_id):
        client = self._client(session, client_id)
        if client is None:
            return
        answer = QMessageBox.question(self, "Disconnect user",
                                      f"Disconnect {client['name']} from session {session}?")
        if answer == QMessageBox.Yes:
            self._request("POST", f"/api/admin/docs/{quote(session, safe='')}/clients/{client_id}/kick",
                          callback=self._after_action)


def main():
    parser = argparse.ArgumentParser(description="Admin panel for the Spice collaboration server")
    parser.add_argument("--server", default="127.0.0.1:5000", help="server address (host:port)")
    parser.add_argument("--token", default="", help="admin token printed by server.py")
    args = parser.parse_args()  # before Qt, so -h and errors exit cleanly

    app = QApplication(sys.argv)
    widget = AdminWidget(args.server, args.token)
    widget.show()
    if args.token:
        widget.start()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
