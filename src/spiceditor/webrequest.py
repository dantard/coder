"""
Asynchronous HTTP requests for Qt code, done with urllib.

Each request runs in a background thread; the result is delivered on the
Qt (GUI) thread by calling ``callback(ok, status, body)``:

    ok      True for a 2xx answer
    status  the HTTP status code, 0 if the server could not be reached
    body    the response body (bytes, may be empty)

urllib uses Python's own ssl module, so https:// works wherever Python
does, independently of the OpenSSL version Qt was built against.
"""
import json
import ssl
import threading
import urllib.error
import urllib.request

from PyQt5.QtCore import QObject, pyqtSignal

try:
    import certifi
    _SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    _SSL_CONTEXT = ssl.create_default_context()

_live = set()   # requests still running: keep them alive until delivered


class Request(QObject):
    _done = pyqtSignal(int, bytes)

    def __init__(self, method, url, payload, headers, timeout, callback):
        super().__init__()
        self.callback = callback
        self.aborted = False
        self._done.connect(self._deliver)   # queued: emitted from the worker thread

        data = None
        headers = dict(headers or {})
        if payload is not None:
            data = json.dumps(payload).encode()
            headers["Content-Type"] = "application/json"
        self._request = urllib.request.Request(url, data=data, headers=headers, method=method)
        self._timeout = timeout

        _live.add(self)
        threading.Thread(target=self._run, daemon=True).start()

    def abort(self):
        """Forget the request: its callback will not be called. (urllib
        cannot interrupt a request in progress; the thread just ends when
        the server answers or the timeout expires.)"""
        self.aborted = True

    def _run(self):
        try:
            with urllib.request.urlopen(self._request, timeout=self._timeout,
                                        context=_SSL_CONTEXT) as response:
                status, body = response.status, response.read()
        except urllib.error.HTTPError as e:     # the server answered 4xx / 5xx
            status = e.code
            try:
                body = e.read()
            except OSError:
                body = b""
        except Exception:                       # unreachable, timeout, TLS error, ...
            status, body = 0, b""
        try:
            self._done.emit(status, body)
        except RuntimeError:                    # Qt object already gone (app quitting)
            pass

    def _deliver(self, status, body):
        _live.discard(self)
        if not self.aborted and self.callback:
            self.callback(200 <= status < 300, status, body)


def get(url, callback=None, headers=None, timeout=10):
    return Request("GET", url, None, headers, timeout, callback)


def post(url, payload, callback=None, headers=None, timeout=10):
    return Request("POST", url, payload or {}, headers, timeout, callback)
