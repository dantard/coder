from PyQt5.QtCore import Qt, QRegExp
from PyQt5.QtGui import QIntValidator, QRegExpValidator
from PyQt5.QtWidgets import QPushButton, QTextEdit, QVBoxLayout, QDialog, QTabWidget, QWidget

import sys
from PyQt5.QtWidgets import (
    QApplication, QDialog, QDialogButtonBox,
    QFormLayout, QLineEdit, QVBoxLayout
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
    def __init__(self, userid, parent=None, session="1", host="127.0.0.1", port="5000"):
        super().__init__(parent)
        self.setWindowTitle("Connect this tab")

        # Fields
        self.user_id_edit = QLineEdit(userid)
        self.host_address_edit = QLineEdit(host)
        self.host_port_edit = QLineEdit(str(port))
        self.host_port_edit.setValidator(QIntValidator(1, 65535, self))
        self.session_edit = QLineEdit(session)
        # the server accepts letters, digits, '-' and '_' (max 64)
        self.session_edit.setValidator(QRegExpValidator(QRegExp(r"[A-Za-z0-9_-]{1,64}"), self))
        self.session_edit.setToolTip("Tabs that join the same session share the same code")

        # Form layout
        form = QFormLayout()
        form.addRow("User name:", self.user_id_edit)
        form.addRow("Server Address:", self.host_address_edit)
        form.addRow("Server Port:", self.host_port_edit)
        form.addRow("Session:", self.session_edit)

        # OK / Cancel buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.ok_button = buttons.button(QDialogButtonBox.Ok)
        for edit in (self.user_id_edit, self.host_address_edit, self.host_port_edit, self.session_edit):
            edit.textChanged.connect(self.update_ok_button)

        # Main layout
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)
        self.update_ok_button()

    def update_ok_button(self):
        self.ok_button.setEnabled(all(e.hasAcceptableInput() and e.text().strip() for e in
                                      (self.user_id_edit, self.host_address_edit,
                                       self.host_port_edit, self.session_edit)))

    def get_values(self):
        return {
            "user_id": self.user_id_edit.text().strip(),
            "host_address": self.host_address_edit.text().strip(),
            "host_port": self.host_port_edit.text().strip(),
            "session": self.session_edit.text().strip(),
        }
