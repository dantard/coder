# Spice User Manual

**Version 0.0.8** — A Python IDE for Students  
Author: Danilo Tardioli · Universidad de Zaragoza  
License: GPL-3.0 · Repository: https://github.com/dantard/coder

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [System Requirements](#2-system-requirements)
3. [Installation](#3-installation)
4. [Launching Spice](#4-launching-spice)
5. [Interface Overview](#5-interface-overview)
6. [Writing and Editing Code](#6-writing-and-editing-code)
7. [Running Programs](#7-running-programs)
8. [Interactive Console](#8-interactive-console)
9. [PDF Viewer](#9-pdf-viewer)
10. [Code Formatting](#10-code-formatting)
11. [Terminal](#11-terminal)
12. [Keyboard Shortcuts](#12-keyboard-shortcuts)
13. [Troubleshooting](#13-troubleshooting)
14. [Contributing](#14-contributing)

---

## 1. Introduction

Spice is a lightweight, open-source Python IDE designed specifically for students in introductory and intermediate programming courses. Unlike full-featured professional IDEs, Spice focuses on the essentials: writing, running, and understanding Python code, without unnecessary complexity getting in the way.

Spice was developed at the Universidad de Zaragoza as a practical response to a common problem in teaching environments — existing tools are either too simple (basic text editors with no interactivity) or too complex (professional IDEs that overwhelm beginners with menus, panels, and configuration options). Spice occupies the middle ground: it is a real, capable IDE with an interactive console, automatic formatting, and an integrated PDF viewer, but it presents these features in a clear and approachable way.

This manual covers everything you need to install, configure, and use Spice effectively in a course or self-study context.

---

## 2. System Requirements

Before installing Spice, make sure your system meets the following requirements.

**Operating System**

Spice runs on Windows, macOS, and Linux. It has been tested on Ubuntu 20.04+, macOS 12+, and Windows 10/11.

**Python**

Python 3.10 or higher is required. You can check your Python version by running:

```bash
python3 --version
```

If Python is not installed, download it from https://www.python.org/downloads/.

**pip**

pip (the Python package manager) is required for installation. It is included with all modern Python distributions. Verify it with:

```bash
pip3 --version
```

---

## 3. Installation

### Standard Installation (recommended)

Install Spice directly from PyPI using pip:

```bash
pip install spiceditor
```

This will automatically install all required dependencies:

- `pyqt5` — graphical user interface framework
- `pymupdf` — PDF rendering engine
- `autopep8` — automatic PEP 8 code formatter
- `scipy` — scientific computing library
- `qtconsole` — interactive Python console widget
- `termqt` — terminal widget
- `easyconfig2` — configuration management
- `pyshortcuts` — desktop shortcut creation

### Installation from Source

If you prefer to install from the source repository:

```bash
git clone https://github.com/dantard/coder.git
cd coder
pip install .
```

### Creating Desktop Shortcuts

After installation, run the following command to create shortcuts in your operating system's application launcher or desktop:

```bash
spiceinstall
```

This is particularly useful in lab environments where students may not be comfortable using the terminal to launch applications each time.

---

## 4. Launching Spice

There are three ways to open Spice after installation.

**From the terminal:**

```bash
spice
```

**From a desktop shortcut:**  
If you ran `spiceinstall`, a shortcut will be available in your application menu or on your desktop depending on your operating system.

**Opening a specific file:**

```bash
spice myprogram.py
```

---

## 5. Interface Overview

The Spice interface is divided into several main areas:

```
┌─────────────────────────────────────────────────────┐
│  Menu Bar                                           │
├──────────────────────────────┬──────────────────────┤
│                              │                      │
│        Code Editor           │    PDF Viewer        │
│                              │   (optional panel)   │
│                              │                      │
├──────────────────────────────┴──────────────────────┤
│              Interactive Console                    │
└─────────────────────────────────────────────────────┘
```

**Menu Bar** — Access file operations, run controls, view options, and settings.

**Code Editor** — The main area where you write your Python programs. It provides syntax highlighting, line numbers, and automatic indentation.

**Interactive Console** — A live Python interpreter panel at the bottom of the window. You can type and evaluate Python expressions here at any time, independently of the file you are editing.

**PDF Viewer** — An optional side panel that renders PDF documents. Useful for consulting lab assignment sheets without leaving the IDE.

---

## 6. Writing and Editing Code

### Creating a New File

Go to **File → New** or press `Ctrl+N`. A blank editor tab will open.

### Opening an Existing File

Go to **File → Open** or press `Ctrl+O`. Navigate to your `.py` file and click Open.

### Saving

- **Save:** `Ctrl+S`
- **Save As:** `Ctrl+Shift+S`

### Syntax Highlighting

Spice automatically applies color highlighting to Python syntax elements: keywords, strings, comments, function names, and numbers. This is always active and requires no configuration.

### Auto-indentation

When you press `Enter` after a line ending with a colon (e.g., `def`, `if`, `for`, `while`, `class`), Spice automatically indents the next line by four spaces, following PEP 8 conventions.

### Line Numbers

Line numbers are displayed on the left margin of the editor. These are helpful when an error message refers to a specific line.

---

## 7. Running Programs

### Running the Current File

Press `F5` or go to **Run → Run** to execute the currently open file. The output will appear in the console panel at the bottom of the screen.

### Stopping Execution

If your program is running and you need to stop it (for example, if it is stuck in an infinite loop), press `Ctrl+C` in the console panel, or go to **Run → Stop**.

### Viewing Output

All `print()` statements and error messages appear in the console panel. Errors include a traceback showing which line caused the problem.

---

## 8. Interactive Console

The interactive console at the bottom of the Spice window is a fully functional Python interpreter. You can use it to:

- Test small code snippets before adding them to your program
- Inspect the value of variables after running your script
- Import libraries and explore their functions
- Perform quick calculations

**Example session:**

```python
>>> x = 10
>>> y = 3
>>> x / y
3.3333333333333335
>>> import math
>>> math.sqrt(2)
1.4142135623730951
```

The console retains its state between commands during the same session. If you want to reset it (clear all variables and imports), restart the kernel from the console menu.

---

## 9. PDF Viewer

Spice includes a built-in PDF viewer panel, powered by PyMuPDF. This allows you to open and read PDF documents — such as lab assignment sheets or course notes — directly inside the IDE, without needing to switch to a separate application.

### Opening a PDF

Go to **View → Open PDF** and select your file. The PDF will open in the side panel.

### Navigation

- Scroll through pages using the mouse wheel or the scroll bar.
- Use the navigation arrows at the top of the panel to jump between pages.

### Resizing the Panel

Drag the divider between the code editor and the PDF panel to adjust the relative sizes of each area.

---

## 10. Code Formatting

Spice integrates `autopep8` to automatically format your code according to PEP 8, the official Python style guide. This helps you develop good coding habits without needing to memorize all the style rules.

### Formatting the Current File

Go to **Code → Format** or press `Ctrl+Shift+F`. Spice will reformat your entire file: fixing indentation, spacing around operators, blank lines between functions, and other style issues.

### What Gets Fixed Automatically

- Incorrect indentation (e.g., 2-space or 3-space indent corrected to 4 spaces)
- Missing spaces around operators (`x=1` → `x = 1`)
- Excess blank lines
- Lines that are too long (wrapped where possible)
- Missing whitespace after commas

---

## 11. Terminal

In addition to the interactive Python console, Spice provides access to a standalone terminal via the `spiceterm` command:

```bash
spiceterm
```

This opens a terminal window integrated with the Spice environment. You can use it to run shell commands, navigate directories, install packages, or run scripts from the command line without leaving your workflow.

---

## 12. Keyboard Shortcuts

| Action | Shortcut |
|---|---|
| New file | `Ctrl+N` |
| Open file | `Ctrl+O` |
| Save | `Ctrl+S` |
| Save As | `Ctrl+Shift+S` |
| Run program | `F5` |
| Stop execution | `Ctrl+C` |
| Format code | `Ctrl+Shift+F` |
| Undo | `Ctrl+Z` |
| Redo | `Ctrl+Y` |
| Find | `Ctrl+F` |
| Comment/Uncomment line | `Ctrl+/` |
| Increase font size | `Ctrl++` |
| Decrease font size | `Ctrl+-` |

---

## 13. Troubleshooting

**Spice does not start after installation**  
Make sure Python 3.10+ is installed and that the `spice` command is in your system PATH. Try running `pip show spiceditor` to confirm the package is installed correctly.

**PyQt5 errors on Linux**  
On some Linux distributions you may need to install additional system dependencies:
```bash
sudo apt install python3-pyqt5
```

**The console does not respond**  
Restart the console kernel from the console menu, or close and reopen Spice.

**PDF file does not open**  
Ensure the file is not corrupted or password-protected. Spice's PDF viewer does not support encrypted PDFs.

**Code formatting breaks my code**  
`autopep8` only applies safe style changes and will not alter the logic of your program. If you believe a formatting change is incorrect, use `Ctrl+Z` to undo and report the issue at the repository.

---

## 14. Contributing

Spice is open-source software released under the GPL-3.0 license. Contributions are welcome.

**Repository:** https://github.com/dantard/coder  
**Report bugs or request features:** https://github.com/dantard/coder/issues  
**Author:** Danilo Tardioli · dantard@unizar.es

To contribute code, fork the repository, create a branch with your changes, and open a pull request. Please ensure your code follows PEP 8 style conventions and includes appropriate comments.

---

*Spice v0.0.8 — Universidad de Zaragoza — GPL-3.0*
