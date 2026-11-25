import json

try:
    from spiceditor import webrequest
except ImportError:  # running from this folder
    import webrequest

from PyQt5.QtCore import Qt, QRegExp, QTimer
from PyQt5.QtGui import QIntValidator, QRegExpValidator
from PyQt5.QtWidgets import QPushButton, QTextEdit, QVBoxLayout, QDialog, QTabWidget, QWidget

import sys
from PyQt5.QtWidgets import (
    QApplication, QDialog, QDialogButtonBox,
    QFormLayout, QLineEdit, QVBoxLayout,
    QButtonGroup, QGroupBox, QHBoxLayout, QHeaderView, QLabel, QRadioButton,
    QTreeWidget, QTreeWidgetItem
)


class Author(QDialog):
    def __init__(self):
        super().__init__()
        self.setLayout(QVBoxLayout())
        self.setMinimumSize(420, 370)
        self.setMaximumSize(420, 420)
        self.setWindowTitle("About")
        self.tabs = QTabWidget()
        self.layout().addWidget(self.tabs)

        textEdit = QTextEdit()
        textEdit.setReadOnly(True)
        textEdit.setHtml("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SPICE - About</title>
    <style>
        body {
            font-family: 'Arial', sans-serif;
            background-color: #f4f4f9;
            color: #333;
            margin: 0;
            padding: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            text-align: center;
        }

        .container {
            background-color: #ffffff;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
            width: 80%;
            max-width: 600px;
        }

        h1 {
            font-size: 3em;
            color: #2c3e50;
            margin-bottom: 20px;
        }

        p {
            font-size: 1.2em;
            line-height: 1.6;
        }

        ul {
            list-style: none;
            padding: 0;
        }

        ul li {
            font-size: 1.1em;
            margin: 5px 0;
        }

        .footer {
            font-size: 1em;
            color: #7f8c8d;
            margin-top: 20px;
        }

        .footer p {
            margin: 0;
        }

    </style>
</head>
<body>

    <div class="container">
        <h1>Spice</h1>
        <h2><strong>Slides and Python for Interactive and Creative Education</strong></h2>

        <h4><strong>Developed by:</strong></h4>
            <h2>Danilo Tardioli</h2>
            <h3>Email: <a href="mailto:dantard@unizar.es">dantard@unizar.es</a></h3>

        <p><strong>Year:</strong> 2024</p>

        <div class="footer">
            <p><strong>Learn more at:</strong> <a href="https://github.com/dantard/coder">https://github.com/dantard/coder</a></p>
        </div>
    </div>

</body>
</html>

        """)
        textEdit2 = QTextEdit()
        textEdit2.setReadOnly(True)
        textEdit2.setHtml("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SPICE - Shortcuts</title>
    <style>
        body {
            font-family: 'Arial', sans-serif;
            background-color: #f4f4f9;
            color: #333;
            margin: 0;
            padding: 20px;
        }
        h1 {
            font-size: 2.5em;
            color: #2c3e50;
            margin-bottom: 20px;
            text-align: center;
        }
table {
    width: 70%;
    margin: 0 auto 20px auto;
    border-collapse: collapse;
    border: 1px solid #ddd;
}

th, td {
padding: 4px 10px;
    line-height: 1.1;
        text-align: left;
}
        th {
            background-color: #f2f2f2;
        }
        tr:hover {
            background-color: #f1f1f1;
        }
        .footer {
            font-size: 1em;
            color: #7f8c8d;
            text-align: center;
        }
    </style>
</head>
<body>
    <table>
       <tr>
    <th>Action</th>
    <th>Shortcut</th>
</tr>
<tr>
    <td>Autocomplete</td>
    <td>Tab</td>
</tr>
<tr>
    <td>Execute Code</td>
    <td>Ctrl + Enter</td>
</tr>
<tr>
    <td>Execute Single Line</td>
    <td>Ctrl + Shift + Enter</td>
</tr>

<tr>
    <td>Save</td>
    <td>Ctrl + S</td>
</tr>
<tr>
    <td>Save As</td>
    <td>Ctrl + Shift + S</td>
</tr>

<tr>
    <td>New Editor Tab</td>
    <td>Ctrl + E</td>
</tr>
<tr>
    <td>Change Tab</td>
    <td>F1 – F10</td>
</tr>

<tr>
    <td>Execute line and Advance</td>
    <td>F11</td>
</tr>

<tr>
    <td>Execute whole code</td>
    <td>F12</td>
</tr>

<tr>
    <td>Fullscreen</td>
    <td>Ctrl + L</td>
</tr>

<tr>
    <td>Toggle Visualization</td>
    <td>Ctrl + K</td>
</tr>
<tr>
    <td>Toggle Dark Mode</td>
    <td>Ctrl + M</td>
</tr>
<tr>
    <td>Change Text Size</td>
    <td>Ctrl + (+ / -)</td>
</tr>             
        
    </table>
</body>
</html>
        """)

        self.tabs.addTab(textEdit, "About")
        self.tabs.addTab(textEdit2, "Shortcuts")
        close_button = QPushButton("Close")
        close_button.setMaximumWidth(100)
        # center the button
        self.layout().addWidget(close_button)
        self.layout().setAlignment(close_button, Qt.AlignRight)
        close_button.clicked.connect(self.close)


class ConnectionDialog(QDialog):
    """Connect a tab: either join a session that exists on the server
    (listed from GET /api/sessions) or create a new one."""

    def __init__(self, userid, parent=None, session="1", host="127.0.0.1", port="5000"):
        super().__init__(parent)
        self.setWindowTitle("Connect this tab")
        self.fallback_session = session     # used if the server cannot be reached
        self.existing = set()               # session names on the server
        self.list_reply = None

        # connection fields
        self.user_id_edit = QLineEdit(userid)
        self.host_address_edit = QLineEdit(host)
        self.host_port_edit = QLineEdit(str(port))
        self.host_port_edit.setValidator(QIntValidator(1, 65535, self))

        form = QFormLayout()
        form.addRow("User name:", self.user_id_edit)
        form.addRow("Server Address:", self.host_address_edit)
        form.addRow("Server Port:", self.host_port_edit)

        # join an existing session
        self.join_radio = QRadioButton("Join an existing session:")
        self.sessions_tree = QTreeWidget()
        self.sessions_tree.setHeaderLabels(["Session", "Connected", "Size"])
        self.sessions_tree.setRootIsDecorated(False)
        self.sessions_tree.setMinimumHeight(140)
        header = self.sessions_tree.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.sessions_tree.itemSelectionChanged.connect(lambda: self.join_radio.setChecked(True))
        self.sessions_tree.itemSelectionChanged.connect(self.update_ok_button)
        self.sessions_tree.itemDoubleClicked.connect(lambda *_: self.ok_button.isEnabled() and self.accept())
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.load_sessions)
        self.list_status = QLabel()

        # create a new session
        self.create_radio = QRadioButton("Create a new session:")
        self.session_edit = QLineEdit(session)
        # the server accepts letters, digits, '-' and '_' (max 64)
        self.session_edit.setValidator(QRegExpValidator(QRegExp(r"[A-Za-z0-9_-]{1,64}"), self))
        self.session_edit.textEdited.connect(lambda: self.create_radio.setChecked(True))
        self.create_hint = QLabel()
        self.create_hint.setStyleSheet("color: #c0392b;")

        mode = QButtonGroup(self)
        mode.addButton(self.join_radio)
        mode.addButton(self.create_radio)
        self.create_radio.setChecked(True)
        mode.buttonToggled.connect(lambda *_: self.update_ok_button())

        join_row = QHBoxLayout()
        join_row.addWidget(self.join_radio)
        join_row.addStretch()
        join_row.addWidget(self.refresh_button)
        create_row = QHBoxLayout()
        create_row.addWidget(self.create_radio)
        create_row.addWidget(self.session_edit, 1)

        box = QGroupBox("Session")
        box_layout = QVBoxLayout(box)
        box_layout.addLayout(join_row)
        box_layout.addWidget(self.sessions_tree)
        box_layout.addWidget(self.list_status)
        box_layout.addSpacing(6)
        box_layout.addLayout(create_row)
        box_layout.addWidget(self.create_hint)

        # OK / Cancel buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.ok_button = buttons.button(QDialogButtonBox.Ok)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(box)
        layout.addWidget(buttons)
        self.resize(460, 460)

        for edit in (self.user_id_edit, self.host_address_edit, self.host_port_edit, self.session_edit):
            edit.textChanged.connect(self.update_ok_button)
        # reload the list when the server changes (after a short pause in typing)
        self.reload_timer = QTimer(self)
        self.reload_timer.setSingleShot(True)
        self.reload_timer.setInterval(500)
        self.reload_timer.timeout.connect(self.load_sessions)
        self.host_address_edit.textEdited.connect(lambda: self.reload_timer.start())
        self.host_port_edit.textEdited.connect(lambda: self.reload_timer.start())

        self.update_ok_button()
        self.load_sessions()

    # ------------------------------------------------------------------
    # list of sessions on the server
    # ------------------------------------------------------------------
    def load_sessions(self):
        if self.list_reply is not None:
            self.list_reply.abort()
        host, port = self.host_address_edit.text().strip(), self.host_port_edit.text().strip()
        if not host or not port:
            return
        self.list_status.setText("Loading sessions…")
        # an aborted (superseded) request never calls back
        self.list_reply = webrequest.get(f"http://{host}:{port}/api/sessions",
                                         self._on_sessions, timeout=4)

    def _on_sessions(self, ok, status, body):
        self.list_reply = None
        try:
            sessions = json.loads(body)["sessions"] if status == 200 else None
        except (ValueError, KeyError):
            sessions = None

        selected = self.selected_session()
        self.sessions_tree.clear()
        if sessions is None:
            self.existing = set()
            self.list_status.setText("Cannot get the sessions from this server" if status == 0
                                     else f"The server answered HTTP {status}")
            self.join_radio.setEnabled(False)
            self.create_radio.setChecked(True)
            self.update_ok_button()
            return

        self.existing = {s["session"] for s in sessions}
        for s in sessions:
            users = s["users"]
            item = QTreeWidgetItem([s["session"],
                                    f"{len(users)}: {', '.join(users)}" if users else "nobody",
                                    f"{s['length']} chars"])
            item.setToolTip(1, "\n".join(users))
            self.sessions_tree.addTopLevelItem(item)
            if s["session"] == selected:
                item.setSelected(True)
        self.list_status.setText(f"{len(sessions)} session(s) on the server" if sessions
                                 else "No sessions yet: create one")
        self.join_radio.setEnabled(bool(sessions))

        # suggest a free number for a new session, unless the user typed one
        if not self.session_edit.isModified():
            n = 1
            while str(n) in self.existing:
                n += 1
            self.session_edit.setText(str(n))
        # default: join if there is something to join
        if sessions and not self.session_edit.isModified():
            self.join_radio.setChecked(True)
            if not self.sessions_tree.selectedItems():
                self.sessions_tree.topLevelItem(0).setSelected(True)
        self.update_ok_button()

    def selected_session(self):
        items = self.sessions_tree.selectedItems()
        return items[0].text(0) if items else None

    # ------------------------------------------------------------------
    def update_ok_button(self):
        fields_ok = all(e.hasAcceptableInput() and e.text().strip() for e in
                        (self.user_id_edit, self.host_address_edit, self.host_port_edit))
        self.create_hint.setText("")
        if self.join_radio.isChecked():
            session_ok = self.selected_session() is not None
            self.ok_button.setText("Join")
        else:
            name = self.session_edit.text().strip()
            session_ok = self.session_edit.hasAcceptableInput() and bool(name)
            if name in self.existing:
                session_ok = False
                self.create_hint.setText(f"Session {name} already exists: select it in the list to join it")
            self.ok_button.setText("Create")
        self.ok_button.setEnabled(fields_ok and session_ok)

    def done(self, result):
        # closed: a session list still loading must not call back
        if self.list_reply is not None:
            self.list_reply.abort()
            self.list_reply = None
        super().done(result)

    def get_values(self):
        session = (self.selected_session() if self.join_radio.isChecked()
                   else self.session_edit.text().strip())
        return {
            "user_id": self.user_id_edit.text().strip(),
            "host_address": self.host_address_edit.text().strip(),
            "host_port": self.host_port_edit.text().strip(),
            "session": session,
        }
