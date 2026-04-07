#!/usr/bin/env python3
"""
SQLite Browser - embeddable PyQt5 widget.
Run standalone: python sqlite_browser.py [database.db]
"""

import sys
import sqlite3
import os
import csv
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QListWidget, QListWidgetItem,
    QPushButton, QTextEdit, QSplitter, QLabel, QFileDialog,
    QMessageBox, QLineEdit, QHeaderView, QAbstractItemView,
    QMenu, QShortcut, QCompleter, QAbstractItemView as _AIV
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QStringListModel
from PyQt5.QtGui import QFont, QColor, QKeySequence, QTextCursor


# ── Async query worker ────────────────────────────────────────────────────────

class QueryWorker(QThread):
    finished = pyqtSignal(list, list)
    error    = pyqtSignal(str)
    info     = pyqtSignal(str)

    def __init__(self, db_path, sql):
        super().__init__()
        self.db_path = db_path
        self.sql     = sql

    def run(self):
        conn = None
        try:
            conn   = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            statements = [s.strip() for s in self.sql.split(";") if s.strip()]
            last_select = None
            for stmt in statements:
                cursor.execute(stmt)
                upper = stmt.upper().lstrip()
                if upper.startswith(("SELECT", "PRAGMA", "WITH")):
                    last_select = cursor
                else:
                    conn.commit()
            if last_select and last_select.description:
                rows = last_select.fetchall()
                cols = [d[0] for d in last_select.description]
                self.finished.emit(rows, cols)
            else:
                affected = cursor.rowcount if cursor.rowcount >= 0 else 0
                self.info.emit(f"Query OK — {affected} row(s) affected.")
                self.finished.emit([], [])
        except Exception as e:
            self.error.emit(str(e))
        finally:
            if conn:
                conn.close()


# ── SQL Autocompleter ─────────────────────────────────────────────────────────

SQL_KEYWORDS = sorted([
    "SELECT", "FROM", "WHERE", "INSERT", "INTO", "VALUES", "UPDATE", "SET",
    "DELETE", "CREATE", "TABLE", "INDEX", "VIEW", "DROP", "ALTER", "ADD",
    "RENAME", "TO", "PRIMARY", "KEY", "FOREIGN", "REFERENCES", "UNIQUE",
    "NOT", "NULL", "DEFAULT", "AUTOINCREMENT", "IF", "EXISTS", "OR", "REPLACE",
    "AND", "IN", "LIKE", "BETWEEN", "IS", "AS", "ON", "JOIN", "INNER", "LEFT",
    "RIGHT", "OUTER", "CROSS", "NATURAL", "GROUP", "BY", "ORDER", "HAVING",
    "LIMIT", "OFFSET", "DISTINCT", "ALL", "CASE", "WHEN", "THEN", "ELSE",
    "END", "UNION", "INTERSECT", "EXCEPT", "BEGIN", "COMMIT", "ROLLBACK",
    "TRANSACTION", "WITH", "PRAGMA", "EXPLAIN", "ASC", "DESC",
    "CURRENT_TIMESTAMP", "CURRENT_DATE", "CURRENT_TIME",
    "INTEGER", "REAL", "TEXT", "BLOB", "NUMERIC", "BOOLEAN", "DATETIME",
    "DATE", "TIME",
    "COUNT", "SUM", "AVG", "MIN", "MAX", "COALESCE", "IFNULL", "NULLIF",
    "LENGTH", "SUBSTR", "UPPER", "LOWER", "TRIM", "LTRIM", "RTRIM",
    "REPLACE", "INSTR", "PRINTF", "HEX", "TYPEOF", "CAST", "ABS", "ROUND",
    "STRFTIME", "JULIANDAY", "LAST_INSERT_ROWID", "CHANGES", "RANDOM",
    "sqlite_master", "sqlite_sequence", "rowid",
])


class _GutterWidget(QWidget):
    """Left gutter showing In [N]: painted inside the QTextEdit margin."""
    GUTTER_W = 60

    def __init__(self, editor):
        super().__init__(editor)
        self._label = "In [ ]:"
        self.setFixedWidth(self.GUTTER_W)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.show()

    def set_label(self, n):
        self._label = f"In [{n}]:" if n is not None else "In [ ]:"
        self.update()

    def paintEvent(self, event):
        from PyQt5.QtGui import QPainter
        from PyQt5.QtCore import QRect
        p = QPainter(self)
        font = self.font()
        font.setPointSize(max(7, font.pointSize() - 1))
        p.setFont(font)
        p.setPen(QColor(26, 127, 212))
        p.drawText(
            QRect(0, 4, self.GUTTER_W - 4, self.height()),
            Qt.AlignRight | Qt.AlignTop,
            self._label
        )
        p.end()


class SQLTextEdit(QTextEdit):
    """QTextEdit with SQL keyword autocompletion and an In[N]: gutter."""

    GUTTER_W = _GutterWidget.GUTTER_W

    def __init__(self, parent=None):
        super().__init__(parent)
        self._gutter = _GutterWidget(self)
        self.setViewportMargins(self.GUTTER_W, 0, 0, 0)

        self._completer = QCompleter(self)
        self._completer.setWidget(self)
        self._completer.setCompletionMode(QCompleter.PopupCompletion)
        self._completer.setCaseSensitivity(Qt.CaseInsensitive)
        self._completer.setFilterMode(Qt.MatchStartsWith)
        self._model = QStringListModel(SQL_KEYWORDS, self._completer)
        self._completer.setModel(self._model)
        self._completer.activated.connect(self._insert_completion)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._gutter.setGeometry(0, 0, self.GUTTER_W, self.height())

    def set_exec_number(self, n):
        self._gutter.set_label(n)
        self._gutter.setFont(self.font())

    def set_extra_words(self, words):
        combined = sorted(set(SQL_KEYWORDS) | set(w.upper() for w in words) | set(words))
        self._model.setStringList(combined)

    def _insert_completion(self, completion):
        tc = self.textCursor()
        # Select the entire word already typed (the prefix)
        tc.select(QTextCursor.WordUnderCursor)
        tc.insertText(completion.upper() + " ")
        self.setTextCursor(tc)

    def _word_under_cursor(self):
        tc = self.textCursor()
        tc.select(QTextCursor.WordUnderCursor)
        return tc.selectedText()

    def keyPressEvent(self, event):
        popup = self._completer.popup()

        # Let the completer handle navigation keys when popup is visible
        if popup.isVisible() and event.key() in (
            Qt.Key_Enter, Qt.Key_Return, Qt.Key_Escape,
            Qt.Key_Tab, Qt.Key_Backtab
        ):
            event.ignore()
            return

        # Ctrl+Enter/Return → run query (pass to parent, hide popup)
        if event.key() in (Qt.Key_Enter, Qt.Key_Return) and (
            event.modifiers() & Qt.ControlModifier
        ):
            popup.hide()
            super().keyPressEvent(event)
            return

        super().keyPressEvent(event)

        # Don't trigger on modifier-only or control keys
        if event.modifiers() & (Qt.ControlModifier | Qt.AltModifier):
            popup.hide()
            return

        prefix = self._word_under_cursor()
        if len(prefix) < 2:
            popup.hide()
            return

        if prefix != self._completer.completionPrefix():
            self._completer.setCompletionPrefix(prefix)
            popup.setCurrentIndex(self._completer.completionModel().index(0, 0))

        cr = self.cursorRect()
        cr.setWidth(
            popup.sizeHintForColumn(0)
            + popup.verticalScrollBar().sizeHint().width()
        )
        self._completer.complete(cr)


# ── SQL Syntax Highlighter ────────────────────────────────────────────────────

from PyQt5.QtGui import QSyntaxHighlighter, QTextCharFormat, QFont as _QFont
from PyQt5.QtCore import QRegExp

class SQLHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._rules = []

        def rule(pattern, color, bold=False, italic=False):
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(color))
            fmt.setFontWeight(_QFont.Bold if bold else _QFont.Normal)
            if italic:
                fmt.setFontItalic(True)
            self._rules.append((QRegExp(pattern, Qt.CaseInsensitive), fmt))

        # Keywords
        keywords = (
            "SELECT|FROM|WHERE|INSERT|INTO|VALUES|UPDATE|SET|DELETE|"
            "CREATE|TABLE|INDEX|VIEW|DROP|ALTER|ADD|RENAME|TO|"
            "PRIMARY|KEY|FOREIGN|REFERENCES|UNIQUE|NOT|NULL|DEFAULT|"
            "AUTOINCREMENT|IF|EXISTS|OR|REPLACE|"
            "AND|OR|NOT|IN|LIKE|BETWEEN|IS|AS|ON|"
            "JOIN|INNER|LEFT|RIGHT|OUTER|CROSS|NATURAL|"
            "GROUP|BY|ORDER|HAVING|LIMIT|OFFSET|DISTINCT|ALL|"
            "CASE|WHEN|THEN|ELSE|END|UNION|INTERSECT|EXCEPT|"
            "BEGIN|COMMIT|ROLLBACK|TRANSACTION|WITH|PRAGMA|EXPLAIN|"
            "ASC|DESC|CURRENT_TIMESTAMP|CURRENT_DATE|CURRENT_TIME"
        )
        rule(r'\b(' + keywords + r')\b', "#0000ff", bold=True)

        # Functions
        functions = (
            "COUNT|SUM|AVG|MIN|MAX|COALESCE|IFNULL|NULLIF|"
            "LENGTH|SUBSTR|UPPER|LOWER|TRIM|LTRIM|RTRIM|REPLACE|"
            "INSTR|PRINTF|FORMAT|HEX|TYPEOF|CAST|ABS|ROUND|"
            "DATE|TIME|DATETIME|STRFTIME|JULIANDAY|"
            "LAST_INSERT_ROWID|CHANGES|TOTAL_CHANGES|RANDOM"
        )
        rule(r'\b(' + functions + r')\s*(?=\()', "#dcdcaa", bold=True)

        # Types
        types = "INTEGER|REAL|TEXT|BLOB|NUMERIC|BOOLEAN|DATETIME|DATE|TIME"
        rule(r'\b(' + types + r')\b', "#4ec9b0", bold=True)

        # Single-quoted strings
        rule(r"'[^']*'", "#ce9178", bold=True)

        # Double-quoted identifiers
        rule(r'"[^"]*"', "#66ccff", bold=True)

        # Numbers
        rule(r'\b[0-9]+(\.[0-9]+)?\b', "#b5cea8", bold=True)

        # Line comments
        rule(r'--[^\n]*', "#6a9955", italic=True, bold=True)

        # Block comments
        self._block_comment_start = QRegExp(r'/\*')
        self._block_comment_end   = QRegExp(r'\*/')
        self._comment_fmt = QTextCharFormat()
        self._comment_fmt.setForeground(QColor("#6a9955"))
        self._comment_fmt.setFontItalic(True)
        self._comment_fmt.setFontWeight(_QFont.Bold)

    def highlightBlock(self, text):
        # Apply single-line rules
        for pattern, fmt in self._rules:
            idx = pattern.indexIn(text)
            while idx >= 0:
                length = pattern.matchedLength()
                self.setFormat(idx, length, fmt)
                idx = pattern.indexIn(text, idx + length)

        # Multi-line block comments
        self.setCurrentBlockState(0)
        start = 0
        if self.previousBlockState() != 1:
            start = self._block_comment_start.indexIn(text)
        while start >= 0:
            end = self._block_comment_end.indexIn(text, start)
            if end == -1:
                self.setCurrentBlockState(1)
                length = len(text) - start
            else:
                length = end - start + self._block_comment_end.matchedLength()
            self.setFormat(start, length, self._comment_fmt)
            start = self._block_comment_start.indexIn(text, start + length)


# ── Main browser widget ───────────────────────────────────────────────────────

class SQLiteBrowser(QWidget):
    """
    Embeddable SQLite browser.

    Usage:
        browser = SQLiteBrowser()
        browser.open_database("mydb.sqlite")
        layout.addWidget(browser)
    """
    file_modified = pyqtSignal(object, bool)
    focus_in = pyqtSignal(object)
    execute_called = pyqtSignal(object)
    db_opened = pyqtSignal(str)  # emitted with path when a database is opened

    def __init__(self, db_path=None, parent=None):
        super().__init__(parent)
        self.db_path   = None
        self.worker    = None
        self._all_rows = []
        self._all_cols = []
        self._last_sql        = None
        self._last_table      = None
        self._last_select_sql = None
        self._pending_info    = None
        self._exec_counter    = 0
        self._history         = []

        from PyQt5.QtCore import QFileSystemWatcher
        self._watcher = QFileSystemWatcher(self)
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.setInterval(500)
        self._refresh_timer.timeout.connect(self._on_file_changed)
        self._watcher.fileChanged.connect(lambda path: self._refresh_timer.start())

        self._setup_ui()
        if db_path:
            self.open_database(db_path)

    # ── UI construction ───────────────────────────────────────────────────────
    def set_dark_mode(self, dark):
        pass

    def update_config(self):
        pass
    def _setup_ui(self):
        self._font_size = 10
        self._mono_font = QFont("Courier New", self._font_size)
        # Apply monospace as the widget-level font so labels, buttons, lists inherit it
        self.setFont(self._mono_font)
        mono = self._mono_font

        # Root layout: just holds the outer vertical splitter — no margins
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Outer vertical splitter: [main area] / [status] ────────────────
        outer = QSplitter(Qt.Vertical)
        outer.setChildrenCollapsible(False)
        root.addWidget(outer)

        # ── 1. Main horizontal splitter: [left panel] | [right panel] ────────
        main_split = QSplitter(Qt.Horizontal)
        main_split.setChildrenCollapsible(False)
        outer.addWidget(main_split)

        # ── Left vertical splitter: [table list] / [schema] ──────────────────
        left_split = QSplitter(Qt.Vertical)
        left_split.setChildrenCollapsible(False)

        table_panel = QWidget()
        tp_layout   = QVBoxLayout(table_panel)
        tp_layout.setContentsMargins(2, 2, 2, 2)
        tp_layout.setSpacing(2)
        tables_header = QHBoxLayout()
        tables_header.addWidget(QLabel("Tables & Views"))
        tables_header.addStretch()
        self.refresh_btn = QPushButton("⟳")
        tables_header.addWidget(self.refresh_btn)
        tp_layout.addLayout(tables_header)
        self.table_list = QTableWidget()
        self.table_list.setColumnCount(2)
        self.table_list.setHorizontalHeaderLabels(["Type", "Name"])
        self.table_list.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table_list.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table_list.horizontalHeader().setVisible(True)
        self.table_list.verticalHeader().setVisible(False)
        self.table_list.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_list.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table_list.setShowGrid(False)
        self.table_list.setContextMenuPolicy(Qt.CustomContextMenu)
        tp_layout.addWidget(self.table_list)

        left_split.addWidget(table_panel)

        history_panel = QWidget()
        hp_layout     = QVBoxLayout(history_panel)
        hp_layout.setContentsMargins(2, 2, 2, 2)
        hp_layout.setSpacing(2)
        hp_layout.addWidget(QLabel("Query History"))
        self.history_list = QListWidget()
        self.history_list.setWordWrap(True)
        self.history_list.setUniformItemSizes(False)
        hp_layout.addWidget(self.history_list)

        left_split.addWidget(history_panel)
        left_split.setSizes([200, 200])

        # ── Right vertical splitter: [query editor] / [filter+results] ───────
        right_split = QSplitter(Qt.Vertical)
        right_split.setChildrenCollapsible(False)

        # Query editor panel
        editor_panel  = QWidget()
        editor_layout = QVBoxLayout(editor_panel)
        editor_layout.setContentsMargins(2, 2, 2, 2)
        editor_layout.setSpacing(2)

        editor_header = QHBoxLayout()
        editor_header.addWidget(QLabel("SQL Query  (Ctrl+Enter to run)"))
        editor_header.addStretch()

        from PyQt5.QtWidgets import QComboBox
        self.snippets_combo = QComboBox()
        self.snippets_combo.addItem("⚡ Snippets…")
        self._snippets = [
            # label, sql
            ("── CREATE ──", None),
            ("CREATE TABLE",
             'CREATE TABLE "people" (\n    "id"         INTEGER PRIMARY KEY AUTOINCREMENT,\n    "name"       TEXT    NOT NULL,\n    "age"        INTEGER,\n    "created_at" DATETIME DEFAULT CURRENT_TIMESTAMP\n);'),
            ("CREATE TABLE (if not exists)",
             'CREATE TABLE IF NOT EXISTS "people" (\n    "id"   INTEGER PRIMARY KEY AUTOINCREMENT,\n    "name" TEXT NOT NULL,\n    "age"  INTEGER\n);'),
            ("CREATE INDEX",
             'CREATE INDEX IF NOT EXISTS "idx_people_name"\nON "people" ("name");'),
            ("CREATE VIEW",
             'CREATE VIEW "people_view" AS\nSELECT "id", "name", "age" FROM "people";'),
            ("── SELECT ──", None),
            ("SELECT *",
             'SELECT * FROM "people" LIMIT 100;'),
            ("SELECT columns",
             'SELECT "id", "name", "age"\nFROM "people"\nWHERE "name" = \'\'\nORDER BY "name" ASC\nLIMIT 100;'),
            ("SELECT with JOIN",
             'SELECT a."id", a."name", b."age"\nFROM "people" a\nINNER JOIN "people" b ON a."id" = b."id"\nWHERE a."name" = \'\'\nLIMIT 100;'),
            ("SELECT COUNT",
             'SELECT COUNT(*) AS "count" FROM "people";'),
            ("SELECT GROUP BY",
             'SELECT "age", COUNT(*) AS "count"\nFROM "people"\nGROUP BY "age"\nORDER BY "count" DESC;'),
            ("── INSERT ──", None),
            ("INSERT",
             'INSERT INTO "people" ("name", "age")\nVALUES (\'Alice\', 30);'),
            ("INSERT OR REPLACE",
             'INSERT OR REPLACE INTO "people" ("id", "name", "age")\nVALUES (1, \'Alice\', 30);'),
            ("── UPDATE ──", None),
            ("UPDATE",
             'UPDATE "people"\nSET "name" = \'Alice\'\nWHERE "id" = 1;'),
            ("── DELETE ──", None),
            ("DELETE rows",
             'DELETE FROM "people"\nWHERE "id" = 1;'),
            ("DELETE all",
             'DELETE FROM "people";'),
            ("── ALTER ──", None),
            ("ADD COLUMN",
             'ALTER TABLE "people"\nADD COLUMN "email" TEXT;'),
            ("RENAME TABLE",
             'ALTER TABLE "people" RENAME TO "persons";'),
            ("── DROP ──", None),
            ("DROP TABLE",
             'DROP TABLE IF EXISTS "people";'),
            ("DROP VIEW",
             'DROP VIEW IF EXISTS "people_view";'),
            ("── PRAGMA ──", None),
            ("Table info",
             'PRAGMA table_info("people");'),
            ("List tables",
             "SELECT name, type FROM sqlite_master WHERE type IN ('table','view') ORDER BY name;"),
            ("Foreign keys",
             'PRAGMA foreign_key_list("people");'),
            ("DB integrity",
             'PRAGMA integrity_check;'),
        ]
        for label, sql in self._snippets:
            self.snippets_combo.addItem(label)
            # Disable separator items
            if sql is None:
                idx = self.snippets_combo.count() - 1
                self.snippets_combo.model().item(idx).setEnabled(False)

        editor_header.addWidget(self.snippets_combo)
        self.run_btn   = QPushButton("▶")
        self.clear_btn = QPushButton("✕")
        editor_header.addWidget(self.clear_btn)
        editor_header.addWidget(self.run_btn)
        editor_layout.addLayout(editor_header)

        self.query_box = SQLTextEdit()
        self.query_box.setPlaceholderText("Enter SQL here…")
        self.query_box.setFont(mono)
        self._highlighter = SQLHighlighter(self.query_box.document())
        editor_layout.addWidget(self.query_box)

        # Results panel (filter bar + table)
        results_panel  = QWidget()
        results_layout = QVBoxLayout(results_panel)
        results_layout.setContentsMargins(2, 2, 2, 2)
        results_layout.setSpacing(2)

        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Filter:"))
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Type to filter visible rows…")
        filter_row.addWidget(self.filter_edit)
        self.reselect_btn = QPushButton("⟲")
        self.reselect_btn.setCheckable(True)
        self.reselect_btn.setChecked(True)
        self.reselect_btn.setToolTip("Auto-reselect: after UPDATE/DELETE re-run last SELECT")
        filter_row.addWidget(self.reselect_btn)
        results_layout.addLayout(filter_row)

        self.data_table = QTableWidget()
        self.data_table.setAlternatingRowColors(True)
        self.data_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.data_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.data_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.data_table.horizontalHeader().setStretchLastSection(False)
        self.data_table.verticalHeader().setDefaultSectionSize(22)
        self.data_table.setContextMenuPolicy(Qt.CustomContextMenu)
        results_layout.addWidget(self.data_table)

        right_split.addWidget(editor_panel)
        right_split.addWidget(results_panel)
        right_split.setSizes([150, 450])

        main_split.addWidget(left_split)
        main_split.addWidget(right_split)
        main_split.setSizes([200, 700])

        # ── 3. Status/error panel ─────────────────────────────────────────────
        status_panel = QWidget()
        st_layout    = QVBoxLayout(status_panel)
        st_layout.setContentsMargins(2, 2, 2, 2)
        st_layout.setSpacing(2)
        st_layout.addWidget(QLabel("Messages"))
        self.status_label = QTextEdit()
        self.status_label.setReadOnly(True)
        self.status_label.setFont(QFont("Courier New", 9))
        st_layout.addWidget(self.status_label)

        outer.addWidget(status_panel)

        # Main area stretches, status panel starts small but is draggable
        outer.setStretchFactor(0, 1)
        outer.setStretchFactor(1, 0)

        # ── Signals ───────────────────────────────────────────────────────────
        self.refresh_btn.clicked.connect(self.refresh)
        self.snippets_combo.currentIndexChanged.connect(self._on_snippet_selected)
        self.run_btn.clicked.connect(self.run_query)
        self.clear_btn.clicked.connect(self.query_box.clear)
        self.history_list.itemClicked.connect(self._on_history_clicked)
        self.history_list.itemDoubleClicked.connect(self._on_history_double_clicked)
        self.table_list.itemDoubleClicked.connect(self._on_table_double_clicked)
        self.table_list.customContextMenuRequested.connect(self._table_context_menu)
        self.data_table.customContextMenuRequested.connect(self._rows_context_menu)
        self.filter_edit.textChanged.connect(self._apply_filter)

        #QShortcut(QKeySequence("Ctrl+Return"), self, self.run_query)
        QShortcut(QKeySequence("Ctrl+Shift+Enter"),  self, self.run_query)
        QShortcut(QKeySequence("Ctrl+="),      self, lambda: self._change_font_size(+1))
        QShortcut(QKeySequence("Ctrl++"),      self, lambda: self._change_font_size(+1))
        QShortcut(QKeySequence("Ctrl+-"),      self, lambda: self._change_font_size(-1))
        self._resize_buttons()

    def execute_code(self):
        pass

    def _on_snippet_selected(self, index):
        if index <= 0:
            return
        # index 0 is the placeholder, items start at 1
        label, sql = self._snippets[index - 1]
        if sql:
            self.query_box.setPlainText(sql)
        self.snippets_combo.setCurrentIndex(0)

    def _resize_buttons(self):
        from PyQt5.QtGui import QFontMetrics
        h = QFontMetrics(self._mono_font).height() + 8
        for btn in (self.refresh_btn, self.run_btn, self.clear_btn, self.reselect_btn):
            btn.setFixedSize(h, h)

    # ── Font size ─────────────────────────────────────────────────────────────

    def _change_font_size(self, delta):
        self._font_size = max(6, min(32, self._font_size + delta))
        self._mono_font.setPointSize(self._font_size)
        self.setFont(self._mono_font)
        for w in (self.query_box, self.status_label):
            w.setFont(self._mono_font)
        from PyQt5.QtGui import QFontMetrics
        row_h = QFontMetrics(self._mono_font).height() + 6
        self.data_table.setFont(self._mono_font)
        self.data_table.verticalHeader().setDefaultSectionSize(row_h)
        self.data_table.horizontalHeader().setFont(self._mono_font)
        for r in range(self.data_table.rowCount()):
            self.data_table.setRowHeight(r, row_h)
        self.data_table.resizeColumnsToContents()
        self._resize_buttons()

    # ── Database operations ───────────────────────────────────────────────────

    def open_database(self, path):
        try:
            conn = sqlite3.connect(path)
            conn.execute("SELECT name FROM sqlite_master LIMIT 1")
            conn.close()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Cannot open database:\n{e}")
            return
        self.db_path = path
        self.path = path
        self.db_opened.emit(path)
        # Watch the file for external changes
        if self._watcher.files():
            self._watcher.removePaths(self._watcher.files())
        self._watcher.addPath(path)
        self.refresh()
        self._set_status(f"Opened: {path}")
    def on_disk(self):
        return True

    def save_program(self, a=None,b=None):
        pass

    def is_selectable(self):
        return False

    def new_database(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "New SQLite Database", "",
            "SQLite databases (*.db *.sqlite *.sqlite3);;All files (*)"
        )
        if path:
            try:
                conn = sqlite3.connect(path)
                conn.close()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Cannot create database:\n{e}")
                return
            self.open_database(path)

    def browse_open(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open SQLite Database", "",
            "SQLite databases (*.db *.sqlite *.sqlite3 *.s3db);;All files (*)"
        )
        if path:
            self.open_database(path)

    def refresh(self):
        if not self.db_path:
            return
        self.table_list.setRowCount(0)
        try:
            conn = sqlite3.connect(self.db_path)
            cur  = conn.execute(
                "SELECT type, name FROM sqlite_master "
                "WHERE type IN ('table','view') ORDER BY type, name"
            )
            rows = cur.fetchall()
            self.table_list.setRowCount(len(rows))
            for i, (kind, name) in enumerate(rows):
                type_item = QTableWidgetItem("T" if kind == "table" else "V")
                type_item.setTextAlignment(Qt.AlignCenter)
                type_item.setForeground(QColor("#4ec9b0") if kind == "table" else QColor("#dcdcaa"))
                type_item.setData(Qt.UserRole, name)
                name_item = QTableWidgetItem(name)
                name_item.setData(Qt.UserRole, name)
                self.table_list.setItem(i, 0, type_item)
                self.table_list.setItem(i, 1, name_item)
            self.table_list.resizeRowsToContents()
            # Feed table/column names into autocompleter
            extra = []
            cur2 = conn.execute(
                "SELECT name FROM sqlite_master WHERE type IN ('table','view')"
            )
            tables = [r[0] for r in cur2.fetchall()]
            extra.extend(tables)
            for tbl in tables:
                try:
                    cur3 = conn.execute(f'PRAGMA table_info("{tbl}")')
                    extra.extend(row[1] for row in cur3.fetchall())
                except Exception:
                    pass
            self.query_box.set_extra_words(extra)
            conn.close()
        except Exception as e:
            self._set_status(f"Error: {e}", error=True)
            return
        if getattr(self, "_last_sql", None):
            if self._last_sql.strip().upper().startswith(("SELECT", "PRAGMA", "WITH")):
                self._run_sql_silent(self._last_sql)

    # ── Table list interactions ───────────────────────────────────────────────

    def _on_table_double_clicked(self, item):
        name = item.data(Qt.UserRole)
        if name:
            self.query_box.setPlainText(f'SELECT * FROM "{name}" LIMIT 200;')
            self.run_query()

    def _table_context_menu(self, pos):
        item = self.table_list.itemAt(pos)
        if not item:
            return
        name = item.data(Qt.UserRole)
        menu = QMenu(self)
        menu.addAction("SELECT * (200 rows)", lambda: self._quick_query(f'SELECT * FROM "{name}" LIMIT 200;'))
        menu.addAction("COUNT rows",          lambda: self._quick_query(f'SELECT COUNT(*) AS count FROM "{name}";'))
        menu.addAction("Show schema",         lambda: self._quick_query(f'PRAGMA table_info("{name}");'))
        menu.addSeparator()
        menu.addAction("DELETE all rows…",    lambda: self._write_query(f'DELETE FROM "{name}";'))
        menu.addAction("DROP table…",         lambda: self._write_query(f'DROP TABLE "{name}";'))
        menu.exec_(self.table_list.mapToGlobal(pos))

    def _rows_context_menu(self, pos):
        selected = self.data_table.selectionModel().selectedRows()
        if not selected or not self._last_table:
            return
        cols = self._all_cols

        # Clicked cell — used for UPDATE
        clicked_item = self.data_table.itemAt(pos)
        clicked_col  = clicked_item.column() if clicked_item else None

        # Try to find primary key column(s) via PRAGMA
        pk_cols = []
        try:
            conn = sqlite3.connect(self.db_path)
            cur  = conn.execute(f'PRAGMA table_info("{self._last_table}")')
            pk_cols = [row[1] for row in cur.fetchall() if row[5] > 0]
            conn.close()
        except Exception:
            pass

        use_rowid = not pk_cols and "rowid" in cols

        def _where_clause(row):
            """Build WHERE clause for a given table row index."""
            if use_rowid:
                v = self.data_table.item(row, cols.index("rowid")).text()
                return f"rowid = {v}"
            elif pk_cols:
                parts = []
                for pk in pk_cols:
                    if pk in cols:
                        v = self.data_table.item(row, cols.index(pk))
                        vt = v.text() if v else "NULL"
                        try:
                            float(vt); parts.append(f'"{pk}" = {vt}')
                        except ValueError:
                            parts.append(f'"{pk}" = \'{vt}\'')
                return " AND ".join(parts)
            else:
                parts = []
                for c, col in enumerate(cols):
                    v = self.data_table.item(row, c)
                    vt = v.text() if v else "NULL"
                    if vt == "NULL":
                        parts.append(f'"{col}" IS NULL')
                    else:
                        try:
                            float(vt); parts.append(f'"{col}" = {vt}')
                        except ValueError:
                            parts.append(f'"{col}" = \'{vt}\'')
                return " AND ".join(parts)

        menu = QMenu(self)
        count = len(selected)

        # ── UPDATE selected cell ──────────────────────────────────────────────
        if clicked_col is not None and count == 1:
            col_name   = cols[clicked_col]
            cur_val    = clicked_item.text() if clicked_item else ""
            row_idx    = selected[0].row()
            where      = _where_clause(row_idx)
            if where:
                update_sql = f'UPDATE "{self._last_table}"\nSET "{col_name}" = {repr(cur_val)}\nWHERE {where};'
                menu.addAction(f'UPDATE "{col_name}"…', lambda sql=update_sql: self._write_query(sql))
                menu.addSeparator()

        # ── DELETE selected rows ──────────────────────────────────────────────
        def build_delete():
            statements = []
            for idx in selected:
                where = _where_clause(idx.row())
                if where:
                    statements.append(f'DELETE FROM "{self._last_table}" WHERE {where};')
            if statements:
                self._write_query("\n".join(statements))

        menu.addAction(f"DELETE {count} selected row{'s' if count > 1 else ''}…", build_delete)
        menu.exec_(self.data_table.mapToGlobal(pos))

    @staticmethod
    def _sql_color(sql):
        """Return a QColor based on the SQL command type."""
        keyword = sql.strip().upper().split()[0] if sql.strip() else ""
        if keyword in ("SELECT", "PRAGMA", "WITH", "EXPLAIN"):
            return QColor(26, 127, 212)   # cornflower blue — read
        if keyword in ("INSERT", "CREATE", "ADD"):
            return QColor(80, 180, 80)     # green — additive
        if keyword in ("DELETE", "DROP", "TRUNCATE"):
            return QColor(210, 70, 70)     # red — destructive
        if keyword in ("UPDATE", "ALTER", "RENAME"):
            return QColor(210, 150, 50)    # orange — modifying
        return QColor()                    # default

    def _add_to_history(self, sql, n=None):
        self._history.insert(0, (n, sql))
        self._history = self._history[:100]
        self.history_list.clear()
        self.history_list.setWordWrap(True)
        for num, entry in self._history:
            label = " ".join(entry.split())
            prefix = f"[#{num}] " if num is not None else ""
            item  = QListWidgetItem(f"{prefix}{label}")
            item.setData(Qt.UserRole, entry)
            item.setToolTip(entry)
            item.setForeground(self._sql_color(entry))
            self.history_list.addItem(item)

    def _on_history_clicked(self, item):
        sql = item.data(Qt.UserRole)  # full SQL stored separately from label
        if sql:
            self.query_box.setPlainText(sql)

    def _on_history_double_clicked(self, item):
        sql = item.data(Qt.UserRole)
        if sql:
            self.query_box.setPlainText(sql)
            self.run_query()

    def _quick_query(self, sql):
        self.query_box.setPlainText(sql)
        self.run_query()

    def _write_query(self, sql):
        """Write SQL to the query box without running it."""
        self.query_box.setPlainText(sql)

    # ── Query execution ───────────────────────────────────────────────────────

    def _run_sql_silent(self, sql):
        """Run sql without touching the query box, history or _last_sql."""
        if self.worker and self.worker.isRunning():
            self.worker.wait()
        self.run_btn.setEnabled(False)
        self.data_table.clearContents()
        self.data_table.setRowCount(0)
        self._pending_info = None
        self.worker = QueryWorker(self.db_path, sql)
        self.worker.finished.connect(self._on_query_done)
        self.worker.error.connect(self._on_query_error)
        self.worker.info.connect(lambda msg: setattr(self, '_pending_info', msg))
        self.worker.finished.connect(lambda r, c: self.run_btn.setEnabled(True))
        self.worker.error.connect(lambda e: self.run_btn.setEnabled(True))
        self.worker.start()

    def run_query(self):
        if not self.db_path:
            QMessageBox.warning(self, "No database", "Please open a database first.")
            return
        sql = self.query_box.toPlainText().strip()
        if not sql:
            return
        if self.worker and self.worker.isRunning():
            self.worker.wait()

        self._last_sql = sql
        self._exec_counter += 1
        self._current_exec = self._exec_counter
        self.query_box.set_exec_number(self._current_exec)
        self._add_to_history(sql, self._current_exec)
        # Track last SELECT separately so we can re-run it after writes
        import re
        is_read = bool(re.match(r'\s*(SELECT|PRAGMA|WITH)\b', sql, re.IGNORECASE))
        if is_read:
            self._last_select_sql = sql
        m = re.search(r'FROM\s+"?(\w+)"?', sql, re.IGNORECASE)
        self._last_table = m.group(1) if m else None
        self._set_status(f"[#{self._current_exec}] Running…")
        self.run_btn.setEnabled(False)
        self.data_table.clearContents()
        self.data_table.setRowCount(0)

        self.worker = QueryWorker(self.db_path, sql)
        self.worker.finished.connect(self._on_query_done)
        self.worker.error.connect(self._on_query_error)
        self.worker.info.connect(lambda msg: setattr(self, '_pending_info', msg))
        self.worker.finished.connect(lambda r, c: self.run_btn.setEnabled(True))
        self.worker.error.connect(lambda e: self.run_btn.setEnabled(True))
        self._pending_info = None
        self.worker.start()

    def _on_query_done(self, rows, cols):
        self._all_rows = rows
        self._all_cols = cols
        self._populate_table(rows, cols)
        n = getattr(self, "_current_exec", "?")
        if rows or cols:
            msg = f"[#{n}] {len(rows)} row(s) returned."
            if self._pending_info:
                msg = f"[#{n}] {self._pending_info}  |  {len(rows)} row(s) returned."
                self._pending_info = None
            self._set_status(msg)
        else:
            if self.reselect_btn.isChecked() and getattr(self, "_last_select_sql", None):
                self._run_sql_silent(self._last_select_sql)
            else:
                if self._pending_info:
                    self._set_status(f"[#{n}] {self._pending_info}")
                    self._pending_info = None

    def _on_query_error(self, msg):
        n = getattr(self, "_current_exec", "?")
        self._set_status(f"[#{n}] Error: {msg}", error=True)

    def _populate_table(self, rows, cols):
        from PyQt5.QtGui import QFontMetrics
        row_h = QFontMetrics(self._mono_font).height() + 6
        self.data_table.setColumnCount(len(cols))
        self.data_table.setRowCount(len(rows))
        self.data_table.setHorizontalHeaderLabels(cols)
        self.data_table.verticalHeader().setDefaultSectionSize(row_h)
        null_color = QColor(150, 150, 150)
        for r, row in enumerate(rows):
            for c, val in enumerate(row):
                if val is None:
                    cell = QTableWidgetItem("NULL")
                    cell.setForeground(null_color)
                else:
                    cell = QTableWidgetItem(str(val))
                self.data_table.setItem(r, c, cell)
        self.data_table.resizeColumnsToContents()

    # ── Filter ────────────────────────────────────────────────────────────────

    def _apply_filter(self, text):
        if not self._all_cols:
            return
        if not text:
            self._populate_table(self._all_rows, self._all_cols)
            return
        tl = text.lower()
        filtered = [r for r in self._all_rows if any(tl in str(v).lower() for v in r)]
        self._populate_table(filtered, self._all_cols)
        self._set_status(f"{len(filtered)} of {len(self._all_rows)} row(s) shown.")

    # ── Export ────────────────────────────────────────────────────────────────

    def export_csv(self):
        if not self._all_cols:
            QMessageBox.information(self, "Nothing to export", "Run a query first.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export CSV", "", "CSV files (*.csv)")
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(self._all_cols)
                writer.writerows(self._all_rows)
            self._set_status(f"Exported {len(self._all_rows)} rows to {path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", str(e))

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _on_file_changed(self):
        # SQLite may briefly remove+recreate the file; re-add to watcher if needed
        if self.db_path and self.db_path not in self._watcher.files():
            self._watcher.addPath(self.db_path)
        self.refresh()
        self._set_status("Database changed externally — refreshed.")

    def _set_status(self, msg, error=False):
        if error:
            self.status_label.setTextColor(QColor(200, 50, 50))
        else:
            from PyQt5.QtGui import QPalette
            self.status_label.setTextColor(self.palette().color(QPalette.WindowText))
        self.status_label.append(msg)


# ── Standalone main window ────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self, db_path=None):
        super().__init__()
        self.setWindowTitle("Spice ~Vibe~~ SQLite Browser")
        self.resize(1100, 700)

        self.browser = SQLiteBrowser(db_path)
        self.browser.db_opened.connect(self._on_db_opened)
        self.setCentralWidget(self.browser)

        menu      = self.menuBar()
        file_menu = menu.addMenu("File")
        file_menu.addAction("New Database…",  self.browser.new_database,  "Ctrl+N")
        file_menu.addAction("Open Database…", self.browser.browse_open,   "Ctrl+O")
        file_menu.addAction("Refresh",        self.browser.refresh,     "F5")
        file_menu.addSeparator()
        file_menu.addAction("Export CSV…",    self.browser.export_csv)
        file_menu.addSeparator()
        file_menu.addAction("Quit",           self.close,               "Ctrl+Q")

    def _on_db_opened(self, path):
        self.setWindowTitle(f"SQLite Browser — {os.path.basename(path)}")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Spice SQLite Browser")
    db_path = sys.argv[1] if len(sys.argv) > 1 else None
    window = MainWindow(db_path)
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()