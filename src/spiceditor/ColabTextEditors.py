import sys
import json
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget,
    QLineEdit, QPushButton, QLabel, QHBoxLayout,
    QTextEdit, QPlainTextEdit, QMessageBox,
)
from PyQt5.QtNetwork import QTcpServer, QTcpSocket, QHostAddress
from PyQt5.QtGui import (
    QFont, QPainter, QBrush, QPen, QColor,
    QTextCharFormat, QTextCursor,
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject


# ---------------------------------------------------------------------------
# OT Primitives
# ---------------------------------------------------------------------------

class Operation:
    """Represents a text operation: insert or delete."""

    def __init__(self, op_type, position, content="", length=0):
        self.type = op_type
        self.position = position
        self.content = content
        self.length = length

    def to_dict(self):
        return {
            "type": self.type,
            "position": self.position,
            "content": self.content,
            "length": self.length,
        }

    @staticmethod
    def from_dict(d):
        return Operation(
            d["type"], d["position"], d.get("content", ""), d.get("length", 0)
        )

    def apply(self, text):
        if self.type == "insert":
            return text[: self.position] + self.content + text[self.position:]
        if self.type == "delete":
            return text[: self.position] + text[self.position + self.length:]
        return text


class OTEngine:
    """Operational Transformation engine."""

    @staticmethod
    def transform(op1, op2):
        """Transform op1 against op2 (op2 happened concurrently)."""

        if op1.type == "insert" and op2.type == "insert":
            if op2.position <= op1.position:
                return Operation("insert", op1.position + len(op2.content), op1.content)
            return op1

        if op1.type == "insert" and op2.type == "delete":
            if op2.position + op2.length <= op1.position:
                return Operation("insert", op1.position - op2.length, op1.content)
            if op2.position < op1.position:
                return Operation("insert", op2.position, op1.content)
            return op1

        if op1.type == "delete" and op2.type == "insert":
            if op2.position <= op1.position:
                return Operation("delete", op1.position + len(op2.content), length=op1.length)
            if op2.position < op1.position + op1.length:
                return Operation("delete", op1.position, length=op1.length + len(op2.content))
            return op1

        if op1.type == "delete" and op2.type == "delete":
            if op2.position + op2.length <= op1.position:
                return Operation("delete", op1.position - op2.length, length=op1.length)
            if op2.position >= op1.position + op1.length:
                return op1
            overlap_start = max(op1.position, op2.position)
            overlap_end = min(op1.position + op1.length, op2.position + op2.length)
            overlap = overlap_end - overlap_start
            new_pos = op2.position if op2.position <= op1.position else op1.position
            new_len = op1.length - overlap
            if new_len <= 0:
                return Operation("delete", new_pos, length=0)
            return Operation("delete", new_pos, length=new_len)

        return op1


# ---------------------------------------------------------------------------
# Typing-lock overlay widget
# ---------------------------------------------------------------------------

class TypingOverlay(QWidget):
    """
    Semi-transparent overlay painted on top of the editor viewport.
    Shows who is typing and absorbs all input events (blocking editing).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.hide()

        self._message = ""
        self._badge_color = QColor("#888888")
        self._user_id = ""

    def show_for(self, user_id: str, color: str):
        self._badge_color = QColor(color)
        self._user_id = user_id
        self._message = f"User {user_id} is typing"
        self.raise_()
        self.show()
        self.update()

    def hide_overlay(self):
        self.hide()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        painter.fillRect(self.rect(), QColor(20, 20, 20, 30))

        font = QFont("Courier New", 13, QFont.Bold)
        painter.setFont(font)
        fm = painter.fontMetrics()
        text_w = fm.horizontalAdvance(self._message)
        text_h = fm.height()

        pad_x, pad_y = 20, 11
        pill_w = text_w + pad_x * 2
        pill_h = text_h + pad_y * 2
        pill_x = (self.width() - pill_w) // 2
        pill_y = self.height() - pill_h - 12

        badge = QColor(self._badge_color)
        badge.setAlpha(230)
        painter.setBrush(QBrush(badge))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(pill_x, pill_y, pill_w, pill_h, pill_h // 2, pill_h // 2)

        painter.setPen(QPen(Qt.white))
        painter.drawText(pill_x + pad_x, pill_y + pad_y + fm.ascent(), self._message)
        painter.end()

    def mousePressEvent(self, e):   e.accept()

    def mouseReleaseEvent(self, e): e.accept()

    def mouseMoveEvent(self, e):    e.accept()

    def keyPressEvent(self, e):     e.accept()

    def keyReleaseEvent(self, e):   e.accept()

    def wheelEvent(self, e):        e.accept()


# ---------------------------------------------------------------------------
# Shared mixin — all OT, networking, and typing-lock logic
# ---------------------------------------------------------------------------

class CollabMixin:
    """
    Mixin that adds OT-based collaborative editing and typing-lock to any
    Qt text widget. The host class must provide these concrete methods:

        _get_plain_text() -> str
        _set_plain_text(text: str)
        _insert_text_at(position: int, text: str, user_id: str)
        _delete_text_at(position: int, length: int)
        _set_read_only(value: bool)
        viewport()                          # already on QAbstractScrollArea

    And must call:
        _collab_init(user_id, user_color)   # from __init__, after super().__init__
        _collab_text_changed()              # from the textChanged signal handler
        _collab_resize(w, h)               # from resizeEvent
    """

    TYPING_IDLE_MS = 1500

    def _collab_init(self, user_id: str, user_color: str):
        self.user_id = user_id
        self.user_color = user_color

        # OT state
        self.revision = 0
        self.pending_ops: list = []
        self.ot_engine = OTEngine()

        self._last_text = ""
        self._is_remote_update = False

        # Network
        self._server = None
        self._peers: list = []
        self._socket = None
        self._buffers: dict = {}

        self.user_colors: dict = {user_id: user_color}

        # Typing lock
        self._lock_owner = None
        self._i_am_typing = False
        self._idle_timer = QTimer(self)
        self._idle_timer.setSingleShot(True)
        self._idle_timer.setInterval(self.TYPING_IDLE_MS)
        self._idle_timer.timeout.connect(self._release_my_lock)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start_server(self, user_id, color="#000000", port: int = 12345):
        self._collab_init(user_id, color)
        self.textChanged.connect(self._collab_text_changed)
        self._server = QTcpServer(self)
        self._server.newConnection.connect(self._handle_new_peer)
        self._server.listen(QHostAddress.Any, port)
        print(f"[OT] Hosting server on port {port} as user '{user_id}' with color {color}")

    def connect_to_host(self, user_id, color="#000000", host: str = "127.0.0.1", port: int = 12345):
        self._collab_init(user_id, color)
        self.textChanged.connect(self._collab_text_changed)
        self._socket = QTcpSocket(self)
        self._buffers[self._socket] = ""
        self._socket.readyRead.connect(lambda: self._process_data(self._socket))
        self._socket.connected.connect(self._on_connected_to_host)
        self._socket.connectToHost(host, port)
        return self._socket

    # ------------------------------------------------------------------
    # Called by the subclass
    # ------------------------------------------------------------------

    def _collab_resize(self, w: int, h: int):
        self._overlay.setGeometry(0, 0, w, h)

    def _collab_text_changed(self):
        if self._is_remote_update:
            return
        current = self._get_plain_text()
        if current == self._last_text:
            return

        self._acquire_my_lock()

        start = 0
        while (start < len(self._last_text) and start < len(current)
               and self._last_text[start] == current[start]):
            start += 1

        end_old, end_new = len(self._last_text), len(current)
        while (end_old > start and end_new > start
               and self._last_text[end_old - 1] == current[end_new - 1]):
            end_old -= 1
            end_new -= 1

        ops = []
        if end_old > start:
            ops.append(Operation("delete", start, length=end_old - start))
        if end_new > start:
            ops.append(Operation("insert", start, content=current[start:end_new]))

        for op in ops:
            self.revision += 1
            self.pending_ops.append((self.revision, op))
            self._broadcast({
                "type": "operation",
                "operation": op.to_dict(),
                "revision": self.revision,
                "base_revision": self.revision - 1,
                "user_id": self.user_id,
                "color": self.user_color,
            })

        self._last_text = current

    # ------------------------------------------------------------------
    # Typing lock — local
    # ------------------------------------------------------------------

    def _acquire_my_lock(self):
        if self._lock_owner is not None and self._lock_owner != self.user_id:
            return
        if not self._i_am_typing:
            self._i_am_typing = True
            self._lock_owner = self.user_id
            self._broadcast({
                "type": "typing_start",
                "user_id": self.user_id,
                "color": self.user_color,
            })
        self._idle_timer.start()

    def _release_my_lock(self):
        if not self._i_am_typing:
            return
        self._i_am_typing = False
        self._lock_owner = None
        self._broadcast({
            "type": "typing_stop",
            "user_id": self.user_id,
            "color": self.user_color,
        })

    # ------------------------------------------------------------------
    # Typing lock — remote
    # ------------------------------------------------------------------

    def _on_remote_typing_start(self, uid: str, color: str):
        if uid == self.user_id:
            return
        self._lock_owner = uid
        self._set_read_only(True)
        vp = self.viewport()
        self._overlay.setGeometry(0, 0, vp.width(), vp.height())
        self._overlay.show_for(uid, color)
        self.typing_lock_changed.emit(True, uid, color)

    def _on_remote_typing_stop(self, uid: str, color: str):
        if uid == self.user_id:
            return
        if self._lock_owner == uid:
            self._lock_owner = None
        self._set_read_only(False)
        self._overlay.hide_overlay()
        self.typing_lock_changed.emit(False, uid, color)

    # ------------------------------------------------------------------
    # Server-side networking
    # ------------------------------------------------------------------

    def _handle_new_peer(self):
        sock = self._server.nextPendingConnection()
        print("diocane")
        self._peers.append(sock)
        self._buffers[sock] = ""
        sock.readyRead.connect(lambda: self._process_data(sock))
        sock.disconnected.connect(lambda: self._handle_peer_disconnect(sock))

        self._send(sock, {
            "type": "full",
            "text": self._get_plain_text(),
            "revision": self.revision,
        })
        for uid, color in self.user_colors.items():
            self._send(sock, {"type": "user_info", "user_id": uid, "color": color})

        if self._lock_owner is not None:
            owner_color = self.user_colors.get(self._lock_owner, "#888888")
            self._send(sock, {
                "type": "typing_start",
                "user_id": self._lock_owner,
                "color": owner_color,
            })

    def _handle_peer_disconnect(self, sock):
        self._peers = [p for p in self._peers if p is not sock]
        self._buffers.pop(sock, None)
        if self._lock_owner is not None and self._lock_owner != self.user_id:
            self._on_remote_typing_stop(
                self._lock_owner, self.user_colors.get(self._lock_owner, "#888888")
            )

    # ------------------------------------------------------------------
    # Client-side networking
    # ------------------------------------------------------------------

    def _on_connected_to_host(self):
        self._send(self._socket, {
            "type": "user_info",
            "user_id": self.user_id,
            "color": self.user_color,
        })

    # ------------------------------------------------------------------
    # Shared networking helpers
    # ------------------------------------------------------------------

    def _send(self, sock, data: dict):
        if sock and sock.state() == QTcpSocket.ConnectedState:
            sock.write((json.dumps(data) + "\n").encode())

    def _broadcast(self, data: dict, origin_sock=None):
        if self._socket:
            self._send(self._socket, data)
        else:
            for peer in self._peers:
                if peer is not origin_sock:
                    self._send(peer, data)

    def _process_data(self, sock):
        self._buffers[sock] = self._buffers.get(sock, "") + sock.readAll().data().decode()
        while "\n" in self._buffers[sock]:
            line, self._buffers[sock] = self._buffers[sock].split("\n", 1)
            try:
                data = json.loads(line)
                self._apply_payload(data)
                if not self._socket:
                    self._broadcast(data, origin_sock=sock)
            except Exception as exc:
                print(f"[OT] error: {exc}")

    # ------------------------------------------------------------------
    # OT application
    # ------------------------------------------------------------------

    def _apply_payload(self, data: dict):
        uid = data.get("user_id")
        color = data.get("color", "#000000")

        if uid is not None and uid not in self.user_colors:
            self.user_colors[uid] = color

        msg_type = data.get("type")

        if msg_type == "typing_start":
            self._on_remote_typing_start(uid, color)
            return
        if msg_type == "typing_stop":
            self._on_remote_typing_stop(uid, color)
            return

        self._is_remote_update = True

        if msg_type == "operation":
            incoming_op = Operation.from_dict(data["operation"])
            base_rev = data.get("base_revision", 0)
            for pending_rev, pending_op in self.pending_ops:
                if pending_rev > base_rev:
                    incoming_op = self.ot_engine.transform(incoming_op, pending_op)
            self._apply_operation(incoming_op, uid, color)
            self.revision = max(self.revision, data.get("revision", 0))

        elif msg_type == "user_info":
            if uid is not None:
                self.user_colors[uid] = color

        elif msg_type == "full":
            self._set_plain_text(data["text"])
            self._last_text = self._get_plain_text()
            self.revision = data.get("revision", 0)
            self.pending_ops.clear()

        self._is_remote_update = False
        self._on_after_remote_update()

    def _apply_operation(self, op: Operation, uid: int, color: str):
        plain_len = len(self._get_plain_text())
        if op.type == "insert":
            pos = min(op.position, plain_len)
            self._insert_text_at(pos, op.content, uid)
        elif op.type == "delete" and op.length > 0:
            start = min(op.position, plain_len)
            end = min(op.position + op.length, plain_len)
            if end > start:
                self._delete_text_at(start, end - start)
        self._last_text = self._get_plain_text()

    # Hook for subclasses to act after a remote update (e.g. reset color format)
    def _on_after_remote_update(self):
        pass


# ---------------------------------------------------------------------------
# CollabTextEdit — QTextEdit with per-user colors
# ---------------------------------------------------------------------------

class CollabTextEdit(CollabMixin, QTextEdit):
    """
    QTextEdit with OT collaborative editing and per-user text colors.
    Each user's typed characters appear in their assigned color.
    """

    typing_lock_changed = pyqtSignal(bool, str, str)

    def __init__(self, user_id: int = 0, user_color: str = "#e74c3c", parent=None):
        QTextEdit.__init__(self, parent)
        self.setAcceptRichText(False)
        self._apply_font()
        self._collab_init(user_id, user_color)
        self._set_my_color_format()
        self.textChanged.connect(self._collab_text_changed)
        self.cursorPositionChanged.connect(self._on_cursor_moved)
        self._overlay = TypingOverlay(self.viewport())

    # ------------------------------------------------------------------
    # CollabMixin interface implementation
    # ------------------------------------------------------------------

    def _get_plain_text(self) -> str:
        return self.toPlainText()

    def _set_plain_text(self, text: str):
        self.setPlainText(text)

    def _insert_text_at(self, position: int, text: str, user_id: str):
        cursor = self.textCursor()
        cursor.setPosition(position)
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(self.user_colors.get(user_id, "#cccccc")))
        cursor.setCharFormat(fmt)
        cursor.insertText(text)

    def _delete_text_at(self, position: int, length: int):
        cursor = self.textCursor()
        cursor.setPosition(position)
        cursor.setPosition(position + length, QTextCursor.KeepAnchor)
        cursor.removeSelectedText()

    def _set_read_only(self, value: bool):
        self.setReadOnly(value)

    # ------------------------------------------------------------------
    # Color format helpers
    # ------------------------------------------------------------------

    def _set_my_color_format(self):
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(self.user_color))
        self.setCurrentCharFormat(fmt)

    def _on_cursor_moved(self):
        if not self._is_remote_update:
            self._set_my_color_format()

    def _on_after_remote_update(self):
        self._set_my_color_format()

    # ------------------------------------------------------------------
    # Qt overrides
    # ------------------------------------------------------------------

    def resizeEvent(self, event):
        super().resizeEvent(event)
        vp = self.viewport()
        self._collab_resize(vp.width(), vp.height())

    @staticmethod
    def _apply_font():
        pass  # font set after construction in __init__ below

    def __init__(self, user_id: int = 0, user_color: str = "#e74c3c", parent=None):
        QTextEdit.__init__(self, parent)
        self.setAcceptRichText(False)
        font = QFont("Courier New")
        font.setStyleHint(QFont.Monospace)
        font.setPointSize(11)
        self.setFont(font)
        self._collab_init(user_id, user_color)
        self._set_my_color_format()
        self.textChanged.connect(self._collab_text_changed)
        self.cursorPositionChanged.connect(self._on_cursor_moved)


# ---------------------------------------------------------------------------
# CollabPlainTextEdit — QPlainTextEdit without colors
# ---------------------------------------------------------------------------

class CollabPlainTextEdit(CollabMixin, QPlainTextEdit):
    """
    QPlainTextEdit with OT collaborative editing. No per-user text colors
    (QPlainTextEdit only supports uniform document color).
    """

    typing_lock_changed = pyqtSignal(bool, str, str)

    def __init__(self, parent=None):
        QPlainTextEdit.__init__(self, parent)
        font = QFont("Courier New")
        font.setStyleHint(QFont.Monospace)
        font.setPointSize(11)
        self.setFont(font)  # Overlay parented to viewport — never affects layout
        self._overlay = TypingOverlay(self.viewport())

    # ------------------------------------------------------------------
    # CollabMixin interface implementation
    # ------------------------------------------------------------------

    def _get_plain_text(self) -> str:
        return self.toPlainText()

    def _set_plain_text(self, text: str):
        self.setPlainText(text)

    def _insert_text_at(self, position: int, text: str, user_id: str):
        cursor = self.textCursor()
        cursor.setPosition(position)
        cursor.insertText(text)

    def _delete_text_at(self, position: int, length: int):
        cursor = self.textCursor()
        cursor.setPosition(position)
        cursor.setPosition(position + length, QTextCursor.KeepAnchor)
        cursor.removeSelectedText()

    def _set_read_only(self, value: bool):
        self.setReadOnly(value)

    # ------------------------------------------------------------------
    # Qt overrides
    # ------------------------------------------------------------------

    def resizeEvent(self, event):
        super().resizeEvent(event)
        vp = self.viewport()
        self._collab_resize(vp.width(), vp.height())


# ---------------------------------------------------------------------------
# Shared host / peer windows  (work with either editor class)
# ---------------------------------------------------------------------------

COLORS = ["#e74c3c", "#2980b9", "#27ae60", "#8e44ad", "#e67e22", "#16a085"]


class HostWindow(QMainWindow):
    def __init__(self, editor_class=CollabPlainTextEdit, port: int = 12345):
        super().__init__()
        self.setWindowTitle(f"OT Editor — Host (port {port})")
        self.resize(800, 600)

        self.editor = editor_class(user_id="0", user_color=COLORS[0])
        self.editor.start_server(port)
        self.editor.typing_lock_changed.connect(self._on_lock_changed)

        self._base_status = f"🟢 Hosting on port {port}  |  User ID: 0"
        self.status = QLabel(self._base_status)
        self.status.setStyleSheet("padding: 6px; font-family: 'Courier New', monospace;")

        layout = QVBoxLayout()
        layout.addWidget(self.status)
        layout.addWidget(self.editor)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def _on_lock_changed(self, locked: bool, uid: str, color: str):
        if locked:
            self.status.setText(f"🔒 User {uid} is typing…")
            self.status.setStyleSheet(
                f"padding: 6px; font-family: 'Courier New', monospace; "
                f"background: {color}; color: white;"
            )
        else:
            self.status.setText(self._base_status)
            self.status.setStyleSheet("padding: 6px; font-family: 'Courier New', monospace;")


class PeerWindow(QMainWindow):
    def __init__(self, editor_class=CollabPlainTextEdit, user_id: str = "1"):
        super().__init__()
        self.setWindowTitle(f"OT Editor — Peer (user {user_id})")
        self.resize(800, 600)

        color = COLORS[hash(user_id) % len(COLORS)]
        self.editor = editor_class(user_id=user_id, user_color=color)
        self.editor.typing_lock_changed.connect(self._on_lock_changed)

        self.ip_input = QLineEdit("127.0.0.1")
        self.ip_input.setFont(QFont("Courier New", 10))
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self._connect)

        self.status = QLabel(f"⚪ Not connected  |  User ID: {user_id}")
        self.status.setStyleSheet("padding: 6px; font-family: 'Courier New', monospace;")

        top = QHBoxLayout()
        top.addWidget(QLabel("Host IP:"))
        top.addWidget(self.ip_input)
        top.addWidget(self.connect_btn)

        layout = QVBoxLayout()
        layout.addWidget(self.status)
        layout.addLayout(top)
        layout.addWidget(self.editor)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def _connect(self):
        sock = self.editor.connect_to_host(self.ip_input.text())
        sock.connected.connect(self._set_connected)
        sock.errorOccurred.connect(lambda _: self.status.setText("🔴 Connection failed"))
        self.connect_btn.setEnabled(False)
        self.connect_btn.setText("Connecting…")

    def _set_connected(self):
        self.status.setText("🟢 Connected")
        self.connect_btn.setText("Connected")

    def _on_lock_changed(self, locked: bool, uid: str, color: str):
        if locked:
            self.status.setText(f"🔒 User {uid} is typing…")
            self.status.setStyleSheet(
                f"padding: 6px; font-family: 'Courier New', monospace; "
                f"background: {color}; color: white;"
            )
        else:
            self.status.setText("🟢 Connected")
            self.status.setStyleSheet("padding: 6px; font-family: 'Courier New', monospace;")


# ---------------------------------------------------------------------------
# Entry point
#
#   python ot_editor.py 0          → host,  plain (no colors)
#   python ot_editor.py 0 rich     → host,  rich  (per-user colors)
#   python ot_editor.py 1          → peer,  plain
#   python ot_editor.py 1 rich     → peer,  rich
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app = QApplication(sys.argv)

    user_id = sys.argv[1] if len(sys.argv) > 1 else "0"
    use_rich = len(sys.argv) > 2 and sys.argv[2] == "rich"
    editor_cls = CollabTextEdit if use_rich else CollabPlainTextEdit

    if user_id == "0":
        window = HostWindow(editor_class=editor_cls, port=12345)
    else:
        window = PeerWindow(editor_class=editor_cls, user_id=user_id)

    window.show()
    sys.exit(app.exec_())
