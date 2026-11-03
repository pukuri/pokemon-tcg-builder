#!/usr/bin/env python3
"""Compatibility shim for Claude Code.

Claude Code's .claude/settings.json still points at this path. The real logic
now lives in deck_guard.py at the repo root, so we just forward the process
(stdin and argv) there and keep a single implementation for every tool.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.execv(sys.executable, [sys.executable, os.path.join(ROOT, "deck_guard.py")] + sys.argv[1:])
