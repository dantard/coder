"""
Collaborative editor client (PyQt5).

All the client logic lives in CollabClientMixin, which can be combined with
either QTextEdit (CollabTextEdit) or QPlainTextEdit (CollabPlainTextEdit):
  * loads the document from the Flask server
  * turns every local edit into an OT operation and sends it
  * long-polls the server for other users' operations and applies them
  * keeps local and remote edits consistent with the classic OT client
    state machine (synchronized / awaiting confirm / awaiting with buffer)
  * shows the other users' cursors and selections in colour

The editor works as a normal, local editor until connect_to_server() is
called, and goes back to being local after leave().

Run:  python client.py --server http://localhost:5000 --doc mydoc --name Alice
"""
import argparse
import json
import sys
import time
import uuid

from PyQt5.QtCore import QByteArray, QTimer, QUrl, QUrlQuery, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QPainter, QTextCharFormat, QTextCursor
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PyQt5.QtWidgets import QApplication, QTextEdit, QPlainTextEdit

try:
    from spiceditor.ot import TextOperation, transform_index
except ImportError:  # running client.py directly from its folder
    from ot import TextOperation, transform_index


class CollabClientMixin:
    """Collaborative editing for QTextEdit / QPlainTextEdit.

    The concrete class must call _collab_setup() after the Qt constructor
    and must define a ``collab_status = pyqtSignal(str)`` signal.
    """

    LABEL_TIMEOUT = 1.0   # seconds a remote user's name stays visible after they type

    # ------------------------------------------------------------------
    # setup
    # ------------------------------------------------------------------
    def _collab_setup(self):
        self.collab_active = False   # connect_to_server() called, not left
        self._editable = True        # False: the user cannot type (see set_editable)
        self.ready = False           # document loaded and in sync
        self.server = ""
        self.doc_id = ""
        self.user_name = ""
        self.client_id = uuid.uuid4().hex
        self._session = 0            # bumped on every connect/leave

        # OT client state
        self.rev = 0              # last server revision we have applied
        self.outstanding = None   # op sent to the server, waiting for ack
        self.outstanding_id = None
        self.buffer = None        # local ops typed while waiting for ack
        self.shadow = ""          # what the document text was after the last sync
        self.applying_remote = False

        # presence
        self.cursor_version = -1
        self.remote_cursors = {}  # client_id -> {name, color, pos, anchor}
        self._local_selections = []
        self._remote_selections = []
        self._last_typed = {}     # client_id -> time.monotonic() of their last edit

        # repaints while name labels are visible, so they disappear on time
        self.label_timer = QTimer(self)
        self.label_timer.setInterval(250)
        self.label_timer.timeout.connect(self._on_label_timer)

        self._initial_text = ""   # local text to publish if the doc is empty
        self._saved_placeholder = ""

        self.net = None
        self.pending = {}         # QNetworkReply -> (callback, session)
        self.poll_reply = None

        self.document().contentsChanged.connect(self._on_local_change)
        self.cursorPositionChanged.connect(self._schedule_cursor_send)
        self.selectionChanged.connect(self._schedule_cursor_send)

        self.cursor_timer = QTimer(self)
        self.cursor_timer.setSingleShot(True)
        self.cursor_timer.setInterval(120)
        self.cursor_timer.timeout.connect(self._send_cursor)

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------
    def connect_to_server(self, server_url, doc_id, user_name):
        """Join document ``doc_id`` on ``server_url``. If the document on the
        server is empty, the current local text is published to it;
        otherwise the local text is replaced by the server's."""
        if self.collab_active:
            self.leave()
        if "://" not in server_url:
            server_url = "http://" + server_url
        self.server = server_url.rstrip("/")
        self.doc_id = doc_id
        self.user_name = user_name
        self.client_id = uuid.uuid4().hex
        self._session += 1
        self.collab_active = True
        self._initial_text = self.toPlainText()
        self._saved_placeholder = self.placeholderText()

        if self.net is None:
            self.net = QNetworkAccessManager(self)
            self.net.finished.connect(self._on_reply_finished)

        # no local undo stack while collaborating, because undo would also
        # revert other people's edits
        self.setUndoRedoEnabled(False)
        self.setReadOnly(True)
        self.setPlaceholderText("Connecting…")
        self._load()

    def set_editable(self, editable):
        """Let the user type or not. The editor stays enabled: text can still
        be selected, copied and scrolled, and remote edits keep arriving."""
        self._editable = editable
        self.setReadOnly(not editable or (self.collab_active and not self.ready))

    def is_editable(self):
        return self._editable

    def is_collab_connected(self):
        return self.ready

    def leave(self):
        """Tell the server we are gone so our cursor disappears at once,
        and go back to being a local editor."""
        if not self.collab_active:
            return
        was_ready = self.ready
        self.collab_active = False
        self.ready = False
        self._session += 1           # ignore replies still in flight
        if self.poll_reply is not None:
            self.poll_reply.abort()
            self.poll_reply = None
        if was_ready:
            done = []
            self._post("/leave", {"client_id": self.client_id},
                       lambda *a: done.append(True), session=None)
            # give the request a moment to go out before the app quits
            deadline = QTimer()
            deadline.setSingleShot(True)
            deadline.start(500)
            while not done and deadline.isActive():
                QApplication.processEvents()
        self.outstanding = self.outstanding_id = self.buffer = None
        self.remote_cursors = {}
        self._last_typed = {}
        self._refresh_remote_cursors()
        self.setReadOnly(not self._editable)
        self.setUndoRedoEnabled(True)
        self.setPlaceholderText(self._saved_placeholder)
        self._status("disconnected")

    # ------------------------------------------------------------------
    # small HTTP helpers (async, on the Qt event loop)
    # ------------------------------------------------------------------
    def _url(self, path, params=None):
        url = QUrl(f"{self.server}/api/docs/{self.doc_id}{path}")
        if params:
            q = QUrlQuery()
            for k, v in params.items():
                q.addQueryItem(k, str(v))
            url.setQuery(q)
        return url

    def _get(self, path, params, callback, timeout_ms=10000):
        req = QNetworkRequest(self._url(path, params))
        req.setTransferTimeout(timeout_ms)
        reply = self.net.get(req)
        self.pending[reply] = (callback, self._session)
        return reply

    def _post(self, path, payload, callback=None, session=0):
        req = QNetworkRequest(self._url(path))
        req.setHeader(QNetworkRequest.ContentTypeHeader, "application/json")
        req.setTransferTimeout(10000)
        reply = self.net.post(req, QByteArray(json.dumps(payload).encode()))
        # session=None: deliver the reply even after a leave/reconnect
        self.pending[reply] = (callback, self._session if session == 0 else session)
        return reply

    def _on_reply_finished(self, reply):
        callback, session = self.pending.pop(reply, (None, None))
        status = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute) or 0
        body = bytes(reply.readAll()) if reply.isOpen() else b""
        error = reply.error()
        reply.deleteLater()
        if session is not None and session != self._session:
            return                               # stale reply
        data = None
        try:
            data = json.loads(body) if body else None
        except ValueError:
            pass
        if callback:
            ok = error == QNetworkReply.NoError and 200 <= status < 300
            callback(ok, status, data)

    def _status(self, text):
        msg = f"{self.doc_id} — {self.user_name} — {text}"
        if msg != getattr(self, "_last_status", None):
            self._last_status = msg
            self.collab_status.emit(msg)

    # ------------------------------------------------------------------
    # loading
    # ------------------------------------------------------------------
    def _load(self):
        if not self.collab_active:
            return
        self._status("connecting…")
        self._get("", None, self._on_loaded)

    def _on_loaded(self, ok, status, data):
        if not ok:
            self._status(f"cannot reach server (HTTP {status}), retrying…")
            QTimer.singleShot(2000, self._load)
            return
        self.applying_remote = True
        self.setPlainText(data["text"])
        self.applying_remote = False
        self.shadow = data["text"]
        self.rev = data["rev"]
        self.outstanding = self.outstanding_id = self.buffer = None
        self.cursor_version = -1
        self.ready = True
        self.setReadOnly(not self._editable)
        self.setPlaceholderText(self._saved_placeholder)
        self._status("connected")
        self._poll()
        if not data["text"] and self._initial_text and self._editable:
            # empty document on the server: publish what we had locally
            # (never from a non-editable editor: it must not change the doc)
            self.setPlainText(self._initial_text)
        self._initial_text = ""
        self._send_cursor()

    def _resync(self, reason):
        """Something went badly wrong (e.g. server restarted): reload."""
        self.ready = False
        self.setReadOnly(True)
        if self.poll_reply is not None:
            self.poll_reply.abort()
            self.poll_reply = None
        self._status(f"{reason} — reloading")
        QTimer.singleShot(500, self._load)

    # ------------------------------------------------------------------
    # local edits -> operations
    # ------------------------------------------------------------------
    def _on_local_change(self):
        if self.applying_remote or not self.ready:
            return
        new_text = self.toPlainText()
        if new_text == self.shadow:
            return
        op = TextOperation.from_diff(self.shadow, new_text)
        self.shadow = new_text

        if self.outstanding is None:          # synchronized
            self._send_op(op)
        elif self.buffer is None:             # awaiting confirm
            self.buffer = op
        else:                                 # awaiting with buffer
            self.buffer = self.buffer.compose(op)
        self._schedule_cursor_send()

    def _send_op(self, op):
        self.outstanding = op
        self.outstanding_id = uuid.uuid4().hex
        self._post_outstanding()

    def _post_outstanding(self):
        if not self.ready or self.outstanding is None:
            return
        payload = {"client_id": self.client_id, "op_id": self.outstanding_id,
                   "rev": self.rev, "op": self.outstanding.to_json()}
        op_id = self.outstanding_id

        def done(ok, status, data):
            if op_id != self.outstanding_id:
                return                         # already acknowledged via poll
            if status == 409:
                self._resync("out of sync")
            elif not ok:
                self._status("send failed, retrying…")
                QTimer.singleShot(1000, self._post_outstanding)
            # success: the acknowledgement arrives through the poll stream,
            # which keeps the order of operations correct
        self._post("/ops", payload, done)

    # ------------------------------------------------------------------
    # long-polling for server operations
    # ------------------------------------------------------------------
    def _poll(self):
        if not self.ready:
            return
        params = {"since": self.rev, "cv": self.cursor_version,
                  "client_id": self.client_id, "name": self.user_name}
        self.poll_reply = self._get("/poll", params, self._on_poll,
                                    timeout_ms=40000)

    def _on_poll(self, ok, status, data):
        self.poll_reply = None
        if not self.ready:
            return
        if status == 409:
            self._resync("server lost our revision")
            return
        if not ok:
            self._status("connection lost, retrying…")
            QTimer.singleShot(1500, self._poll)
            return
        self._status("connected")
        for item in data["ops"]:
            if item["op_id"] == self.outstanding_id:
                self._on_ack()
            else:
                self._on_remote_op(TextOperation.from_json(item["op"]))
                self._last_typed[item["client_id"]] = time.monotonic()
                self.label_timer.start()
            if not self.ready:                 # a resync was triggered
                return
        if data["rev"] != self.rev:           # should never happen
            self._resync("revision mismatch")
            return
        self.cursor_version = data["cv"]
        self.remote_cursors = {cid: c for cid, c in data["cursors"].items()
                               if cid != self.client_id}
        self._last_typed = {cid: t for cid, t in self._last_typed.items()
                            if cid in self.remote_cursors}
        self._refresh_remote_cursors()
        self._poll()

    def _on_ack(self):
        self.rev += 1
        if self.buffer is None:
            self.outstanding = self.outstanding_id = None
            self._schedule_cursor_send()       # we may have skipped one
        else:
            buf, self.buffer = self.buffer, None
            self._send_op(buf)

    def _on_remote_op(self, op):
        self.rev += 1
        if self.outstanding is not None:
            self.outstanding, op = TextOperation.transform(self.outstanding, op)
            if self.buffer is not None:
                self.buffer, op = TextOperation.transform(self.buffer, op)
        self._apply_to_editor(op)

    def _apply_to_editor(self, op):
        """Apply a remote op through a QTextCursor so the user's own cursor
        and scroll position stay where they are."""
        self.applying_remote = True
        try:
            cursor = QTextCursor(self.document())
            cursor.beginEditBlock()
            pos = 0
            for c in op.ops:
                if isinstance(c, str):
                    cursor.setPosition(pos)
                    cursor.insertText(c)
                    pos += len(c)
                elif c > 0:
                    pos += c
                else:
                    cursor.setPosition(pos)
                    cursor.setPosition(pos - c, QTextCursor.KeepAnchor)
                    cursor.removeSelectedText()
            cursor.endEditBlock()
        finally:
            self.applying_remote = False
        self.shadow = op.apply(self.shadow)
        if self.shadow != self.toPlainText():  # safety net
            self._resync("editor diverged")

    # ------------------------------------------------------------------
    # presence: our cursor -> server, other cursors -> screen
    # ------------------------------------------------------------------
    def _schedule_cursor_send(self):
        if self.ready and not self.applying_remote:
            self.cursor_timer.start()

    def _send_cursor(self):
        # positions are only meaningful against a server revision, so only
        # send them when we have no unacknowledged local edits
        if not self.ready or self.outstanding is not None:
            return
        c = self.textCursor()
        self._post("/cursor", {"client_id": self.client_id, "rev": self.rev,
                               "name": self.user_name,
                               "pos": c.position(), "anchor": c.anchor()})

    def _local_index(self, index):
        """Map a server position to our editor, through unacked local ops."""
        for op in (self.outstanding, self.buffer):
            if op is not None:
                index = transform_index(op, index)
        return min(index, len(self.shadow))

    def setExtraSelections(self, selections):
        """Keep the subclass' own selections (e.g. current line highlight)
        together with the remote users' selections."""
        self._local_selections = list(selections)
        super().setExtraSelections(self._local_selections + self._remote_selections)

    def _refresh_remote_cursors(self):
        selections = []
        for cur in self.remote_cursors.values():
            a, b = self._local_index(cur["anchor"]), self._local_index(cur["pos"])
            if a == b:
                continue
            sel = QTextEdit.ExtraSelection()
            color = QColor(cur["color"])
            color.setAlpha(70)
            fmt = QTextCharFormat()
            fmt.setBackground(color)
            sel.format = fmt
            tc = QTextCursor(self.document())
            tc.setPosition(a)
            tc.setPosition(b, QTextCursor.KeepAnchor)
            sel.cursor = tc
            selections.append(sel)
        self._remote_selections = selections
        super().setExtraSelections(self._local_selections + self._remote_selections)
        self.viewport().update()

    def _label_visible(self, cid):
        """The name is shown only while that user is typing."""
        last = self._last_typed.get(cid)
        return last is not None and time.monotonic() - last < self.LABEL_TIMEOUT

    def _on_label_timer(self):
        self.viewport().update()
        if not any(self._label_visible(cid) for cid in self._last_typed):
            self.label_timer.stop()

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.remote_cursors:
            return
        painter = QPainter(self.viewport())
        small = QFont(self.font())
        if self.font().pointSizeF() > 0:
            small.setPointSizeF(max(7.0, self.font().pointSizeF() * 0.75))
        else:  # font size given in pixels
            small.setPixelSize(max(9, int(self.font().pixelSize() * 0.75)))
        painter.setFont(small)
        fm = painter.fontMetrics()
        for cid, cur in self.remote_cursors.items():
            tc = QTextCursor(self.document())
            tc.setPosition(self._local_index(cur["pos"]))
            rect = self.cursorRect(tc)
            color = QColor(cur["color"])
            painter.fillRect(rect.x(), rect.y(), 2, rect.height(), color)
            if not self._label_visible(cid):
                continue
            label = cur["name"]
            w, h = fm.horizontalAdvance(label) + 6, fm.height()
            y = rect.y() - h if rect.y() - h >= 0 else rect.bottom()
            painter.fillRect(rect.x(), y, w, h, color)
            painter.setPen(Qt.white)
            painter.drawText(rect.x() + 3, y + fm.ascent(), label)
        painter.end()

    def closeEvent(self, event):
        self.leave()
        super().closeEvent(event)


class CollabTextEdit(CollabClientMixin, QTextEdit):
    collab_status = pyqtSignal(str)

    def __init__(self, parent=None):
        QTextEdit.__init__(self, parent)
        self.setAcceptRichText(False)
        self._collab_setup()


class CollabPlainTextEdit(CollabClientMixin, QPlainTextEdit):
    collab_status = pyqtSignal(str)

    def __init__(self, parent=None):
        QPlainTextEdit.__init__(self, parent)
        self._collab_setup()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", default="http://localhost:5000")
    parser.add_argument("--doc", default="welcome")
    parser.add_argument("--name", default=None)
    args = parser.parse_args()

    app = QApplication(sys.argv)
    editor = CollabTextEdit()
    editor.setFont(QFont("Monospace", 11))
    editor.collab_status.connect(editor.setWindowTitle)
    editor.resize(800, 600)
    app.aboutToQuit.connect(editor.leave)
    editor.show()
    editor.connect_to_server(args.server, args.doc,
                             args.name or f"user-{uuid.uuid4().hex[:4]}")
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
