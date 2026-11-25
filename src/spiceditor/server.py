"""
Collaborative editing server (Flask).

The server is the single source of truth. Every document keeps:
  * its current text
  * the full list of operations applied so far (revision = len(history))
  * the cursors of connected users

Clients send an operation together with the revision it was based on.
The server transforms it against everything that happened since that
revision, applies it, appends it to the history and wakes up every client
that is long-polling for changes.

Clients can be muted (their edits are rejected) or disconnected through
the admin API under /api/admin, which needs the admin token in the
X-Admin-Token header. See admin.py for a GUI.

Run:  python server.py --port 5000 [--admin-token SECRET]
"""
import argparse
import hmac
import os
import random
import secrets
import threading
import time

from flask import Flask, abort, jsonify, request

try:
    from spiceditor.ot import TextOperation, transform_index
except ImportError:  # running server.py directly from its folder
    from ot import TextOperation, transform_index

app = Flask(__name__)

POLL_TIMEOUT = 25          # seconds a long-poll request is held open
CURSOR_TTL = 40            # forget users that have not polled for this long
KICK_MEMORY = 3600         # how long a disconnected client id stays refused
ADMIN_TOKEN = os.environ.get("SPICE_ADMIN_TOKEN", "")   # set at startup if empty
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
COLORS = ["#e6194b", "#3cb44b", "#4363d8", "#f58231", "#911eb4",
          "#42d4f4", "#f032e6", "#9a6324", "#469990", "#800000"]


class Document:
    def __init__(self, doc_id, text=""):
        self.id = doc_id
        self.text = text
        self.history = []          # list of (TextOperation, client_id, op_id)
        self.seen_ops = {}         # op_id -> revision (makes POST idempotent)
        self.cursors = {}          # client_id -> dict
        self.muted = set()         # client ids whose edits are rejected
        self.kicked = {}           # client_id -> time it was disconnected by an admin
        self.cursor_version = 0
        self.cond = threading.Condition()
        self.dirty = False

    @property
    def rev(self):
        return len(self.history)

    # all methods below must be called with self.cond held
    def touch(self, client_id, name=None, create=True):
        cur = self.cursors.get(client_id)
        if cur is None and not create:
            return None
        if cur is None:
            used = {c["color"] for c in self.cursors.values()}
            free = [c for c in COLORS if c not in used] or COLORS
            cur = self.cursors[client_id] = {
                "name": name or "anonymous", "color": random.choice(free),
                "pos": 0, "anchor": 0, "seen": time.time()}
            self.cursor_version += 1
        cur["seen"] = time.time()
        if name and cur["name"] != name:
            cur["name"] = name
            self.cursor_version += 1
        return cur

    def expire_cursors(self):
        now = time.time()
        dead = [cid for cid, c in self.cursors.items() if now - c["seen"] > CURSOR_TTL]
        for cid in dead:
            del self.cursors[cid]
            self.muted.discard(cid)
        if dead:
            self.cursor_version += 1
        for cid in [cid for cid, t in self.kicked.items() if now - t > KICK_MEMORY]:
            del self.kicked[cid]

    def public_cursors(self):
        return {cid: {**{k: c[k] for k in ("name", "color", "pos", "anchor")},
                      "muted": cid in self.muted}
                for cid, c in self.cursors.items()}


documents = {}
documents_lock = threading.Lock()


def get_doc(doc_id):
    if not doc_id.replace("-", "").replace("_", "").isalnum() or len(doc_id) > 64:
        abort(400, "invalid document id")
    with documents_lock:
        doc = documents.get(doc_id)
        if doc is None:
            text = ""
            path = os.path.join(DATA_DIR, doc_id + ".txt")
            if os.path.exists(path):
                with open(path, encoding="utf-8") as f:
                    text = f.read()
            doc = documents[doc_id] = Document(doc_id, text)
        return doc


# --------------------------------------------------------------------------
# HTTP API
# --------------------------------------------------------------------------
@app.get("/api/docs/<doc_id>")
def load(doc_id):
    doc = get_doc(doc_id)
    with doc.cond:
        return jsonify(text=doc.text, rev=doc.rev)


@app.post("/api/docs/<doc_id>/ops")
def submit_op(doc_id):
    doc = get_doc(doc_id)
    data = request.get_json(force=True)
    try:
        client_id = str(data["client_id"])
        op_id = str(data["op_id"])
        rev = int(data["rev"])
        op = TextOperation.from_json(data["op"])
    except (KeyError, ValueError, TypeError) as e:
        abort(400, f"bad request: {e}")

    with doc.cond:
        if client_id in doc.kicked:
            return jsonify(error="disconnected by the server"), 410
        if op_id in doc.seen_ops:                   # retry of an op we already have
            return jsonify(rev=doc.seen_ops[op_id])
        if client_id in doc.muted:
            return jsonify(error="muted"), 403
        if rev < 0 or rev > doc.rev:
            return jsonify(error="unknown revision, reload the document"), 409

        # transform against every op the client had not seen yet
        for concurrent, _, _ in doc.history[rev:]:
            op, _ = TextOperation.transform(op, concurrent)

        if op.base_length != len(doc.text):
            return jsonify(error="operation does not fit the document"), 400

        doc.text = op.apply(doc.text)
        doc.history.append((op, client_id, op_id))
        doc.seen_ops[op_id] = doc.rev
        for cur in doc.cursors.values():
            cur["pos"] = transform_index(op, cur["pos"])
            cur["anchor"] = transform_index(op, cur["anchor"])
        doc.dirty = True
        doc.cond.notify_all()
        return jsonify(rev=doc.rev)


@app.post("/api/docs/<doc_id>/cursor")
def update_cursor(doc_id):
    doc = get_doc(doc_id)
    data = request.get_json(force=True)
    try:
        client_id = str(data["client_id"])
        rev = int(data["rev"])
        pos, anchor = int(data["pos"]), int(data["anchor"])
    except (KeyError, ValueError, TypeError) as e:
        abort(400, f"bad request: {e}")

    with doc.cond:
        if client_id in doc.kicked:
            return jsonify(error="disconnected by the server"), 410
        if rev < 0 or rev > doc.rev:
            return jsonify(error="unknown revision"), 409
        # the position refers to revision `rev`: bring it up to date
        for op, _, _ in doc.history[rev:]:
            pos, anchor = transform_index(op, pos), transform_index(op, anchor)
        n = len(doc.text)
        cur = doc.touch(client_id, data.get("name"))
        cur["pos"], cur["anchor"] = min(pos, n), min(anchor, n)
        doc.cursor_version += 1
        doc.cond.notify_all()
    return jsonify(ok=True)


@app.get("/api/docs/<doc_id>/poll")
def poll(doc_id):
    """Long-poll: returns as soon as there are new ops or cursor changes."""
    doc = get_doc(doc_id)
    client_id = request.args.get("client_id", "")
    name = request.args.get("name")
    try:
        since = int(request.args.get("since", 0))
        cursor_version = int(request.args.get("cv", -1))
    except ValueError:
        abort(400, "bad parameters")

    deadline = time.time() + POLL_TIMEOUT
    with doc.cond:
        if client_id in doc.kicked:
            return jsonify(error="disconnected by the server"), 410
        if since > doc.rev:
            return jsonify(error="unknown revision, reload the document"), 409
        if client_id:
            doc.touch(client_id, name)
        while doc.rev == since and doc.cursor_version == cursor_version:
            remaining = deadline - time.time()
            if remaining <= 0:
                break
            doc.cond.wait(remaining)
            if client_id in doc.kicked:
                return jsonify(error="disconnected by the server"), 410
            if client_id:
                # only keep an existing cursor alive: if the client left
                # meanwhile, this request must not bring it back as "anonymous"
                doc.touch(client_id, create=False)
        doc.expire_cursors()
        ops = [{"op": op.to_json(), "client_id": cid, "op_id": oid}
               for op, cid, oid in doc.history[since:]]
        return jsonify(ops=ops, rev=doc.rev, cv=doc.cursor_version,
                       cursors=doc.public_cursors(), muted=client_id in doc.muted)


@app.post("/api/docs/<doc_id>/leave")
def leave(doc_id):
    doc = get_doc(doc_id)
    client_id = str((request.get_json(force=True) or {}).get("client_id", ""))
    with doc.cond:
        if doc.cursors.pop(client_id, None) is not None:
            doc.cursor_version += 1
            doc.cond.notify_all()
        doc.muted.discard(client_id)
    return jsonify(ok=True)


# --------------------------------------------------------------------------
# admin API (needs the admin token)
# --------------------------------------------------------------------------
@app.before_request
def check_admin_token():
    if request.path.startswith("/api/admin/"):
        token = request.headers.get("X-Admin-Token", "")
        if not ADMIN_TOKEN or not hmac.compare_digest(token, ADMIN_TOKEN):
            return jsonify(error="wrong or missing admin token"), 401


@app.get("/api/admin/clients")
def admin_clients():
    """Every session with its connected clients."""
    with documents_lock:
        docs = list(documents.values())
    now = time.time()
    sessions = []
    for doc in sorted(docs, key=lambda d: d.id):
        with doc.cond:
            doc.expire_cursors()
            clients = [{"client_id": cid, "name": c["name"], "color": c["color"],
                        "seen": round(now - c["seen"], 1), "muted": cid in doc.muted}
                       for cid, c in doc.cursors.items()]
            sessions.append({"session": doc.id, "rev": doc.rev,
                             "length": len(doc.text),
                             "clients": sorted(clients, key=lambda c: c["name"].lower())})
    return jsonify(sessions=sessions)


def _check_client(doc, client_id):
    """Call with doc.cond held."""
    if client_id not in doc.cursors:
        abort(404, "no such client in this session")


@app.post("/api/admin/docs/<doc_id>/clients/<client_id>/mute")
def admin_mute(doc_id, client_id):
    muted = bool((request.get_json(silent=True) or {}).get("muted", True))
    doc = get_doc(doc_id)
    with doc.cond:
        _check_client(doc, client_id)
        if muted:
            doc.muted.add(client_id)
        else:
            doc.muted.discard(client_id)
        doc.cursor_version += 1        # wakes the client's poll: it learns at once
        doc.cond.notify_all()
    return jsonify(ok=True, muted=muted)


@app.post("/api/admin/docs/<doc_id>/clients/<client_id>/kick")
def admin_kick(doc_id, client_id):
    doc = get_doc(doc_id)
    with doc.cond:
        _check_client(doc, client_id)
        doc.kicked[client_id] = time.time()
        doc.cursors.pop(client_id, None)
        doc.muted.discard(client_id)
        doc.cursor_version += 1
        doc.cond.notify_all()          # its waiting poll returns 410 now
    return jsonify(ok=True)


# --------------------------------------------------------------------------
# persistence: snapshot every changed document to data/<id>.txt
# --------------------------------------------------------------------------
def saver():
    os.makedirs(DATA_DIR, exist_ok=True)
    while True:
        time.sleep(2)
        with documents_lock:
            docs = list(documents.values())
        for doc in docs:
            with doc.cond:
                if not doc.dirty:
                    continue
                text, doc.dirty = doc.text, False
            tmp = os.path.join(DATA_DIR, doc.id + ".txt.tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(text)
            os.replace(tmp, os.path.join(DATA_DIR, doc.id + ".txt"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--admin-token", default=None,
                        help="token for the admin API (default: $SPICE_ADMIN_TOKEN or a random one)")
    args = parser.parse_args()
    ADMIN_TOKEN = args.admin_token or ADMIN_TOKEN or secrets.token_urlsafe(12)
    print(f" * Admin token: {ADMIN_TOKEN}", flush=True)
    threading.Thread(target=saver, daemon=True).start()
    # threaded=True is required: every client keeps one long-poll request open
    app.run(host=args.host, port=args.port, threaded=True)
