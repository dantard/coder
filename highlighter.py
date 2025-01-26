from PyQt5.QtCore import Qt, QRegExp
from PyQt5.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont


class SyntaxHighlighter(QSyntaxHighlighter):

    def __init__(self, keywords, dark=False):
        super().__init__(None)
        self.highlighting_rules = []
        self.keywords = keywords

        keyword_format = QTextCharFormat()
        if dark:
            keyword_format.setForeground(QColor("cyan"))
        else:
            keyword_format.setForeground(QColor("blue"))
        keyword_format.setFontWeight(QFont.Bold)

        # print(set(keywords))

        self.highlighting_rules += [(f"\\b{k}\\b", keyword_format) for k in self.keywords]

        string_format = QTextCharFormat()
        string_format.setForeground(Qt.magenta)
        self.highlighting_rules.append((r'".*"', string_format))
        self.highlighting_rules.append((r"'.*'", string_format))

        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("green"))
        comment_format.setFontItalic(True)
        self.highlighting_rules.append((r"#.*", comment_format))

    def highlightBlock(self, text):
        for pattern, fmt in self.highlighting_rules:
            expression = QRegExp(pattern)
            index = expression.indexIn(text)
            while index >= 0:
                length = expression.matchedLength()
                self.setFormat(index, length, fmt)
                index = expression.indexIn(text, index + length)

    def get_keywords(self):
        return self.keywords

class PythonHighlighter(SyntaxHighlighter):
    def __init__(self, dark=False):
        super().__init__(['return', 'nonlocal', 'elif', 'assert', 'or', 'yield', 'finally',
                'from', 'global', 'del', 'print', 'None', 'pass', 'class', 'as',
                'break', 'while', 'await', 'async', 'range', 'is', 'True', 'lambda',
                'False', 'in', 'import', 'except', 'continue', 'and', 'raise', 'with',
                'if', 'try', 'for', 'else', 'not', 'def', "input", "int", "float", "str", "list", "dict",
                ], dark)

class PascalHighlighter(SyntaxHighlighter):
    def __init__(self, dark=False):
        super().__init__([
    "and", "array", "asm", "begin", "case", "const", "constructor", "destructor",
    "div", "do", "downto", "else", "end", "file", "for", "function", "goto", "if",
    "implementation", "in", "inherited", "inline", "interface", "label", "mod", "nil",
    "not", "object", "of", "or", "packed", "procedure", "program", "record", "repeat",
    "set", "shl", "shr", "string", "then", "to", "type", "unit", "until", "uses",
    "var", "while", "with", "xor", "AND", "ARRAY", "ASM", "BEGIN", "CASE", "CONST", "CONSTRUCTOR", "DESTRUCTOR",
    "DIV", "DO", "DOWNTO", "ELSE", "END", "FILE", "FOR", "FUNCTION", "GOTO", "IF",
    "IMPLEMENTATION", "IN", "INHERITED", "INLINE", "INTERFACE", "LABEL", "MOD", "NIL",
    "NOT", "OBJECT", "OF", "OR", "PACKED", "PROCEDURE", "PROGRAM", "RECORD", "REPEAT",
    "SET", "SHL", "SHR", "STRING", "THEN", "TO", "TYPE", "UNIT", "UNTIL", "USES",
    "VAR", "WHILE", "WITH", "XOR"
], dark)