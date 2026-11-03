#!/usr/bin/env python3
"""
Deck guard: enforces the deck rules in AGENTS.md.

It works two ways:

1. As a plain command, runnable by any agent, CI, or a human:
       python3 deck_guard.py                 # check every deck in decks/
       python3 deck_guard.py decks/foo.json  # check one deck (or several)

2. As a Claude Code hook (wired up in .claude/settings.json). It reads the
   hook event JSON from stdin and checks a deck as soon as it is written, then
   blocks Claude from stopping until every deck touched this session passes.

Exit codes:
   0 = pass
   1 = fail (CLI mode)
   2 = (hook mode) show errors to Claude / don't stop yet
"""

import json
import os
import subprocess
import sys

MAX_STOP_BLOCKS = 3
DECKS_DIR = "decks"


def project_root():
    """The project directory. Claude Code sets CLAUDE_PROJECT_DIR; any other
    caller can set DECK_GUARD_ROOT, otherwise we assume the current directory."""
    return (os.environ.get("CLAUDE_PROJECT_DIR")
            or os.environ.get("DECK_GUARD_ROOT")
            or os.getcwd())


def run_checker(root, deck):
    checker = os.path.join(root, "check_deck.py")
    result = subprocess.run([sys.executable, checker, deck],
                            cwd=root, capture_output=True, text=True, timeout=120)
    return result.returncode, (result.stdout + result.stderr).strip()


def is_deck_file(root, path):
    if not path:
        return False
    full = os.path.abspath(os.path.join(root, path))
    decks = os.path.abspath(os.path.join(root, DECKS_DIR))
    return full.startswith(decks + os.sep) and full.endswith(".json")


def all_deck_files(root):
    decks = os.path.join(root, DECKS_DIR)
    if not os.path.isdir(decks):
        return []
    return sorted(os.path.join(decks, f) for f in os.listdir(decks)
                  if f.endswith(".json"))


def state_path(root, session):
    folder = os.path.join(root, ".claude", "state")
    os.makedirs(folder, exist_ok=True)
    safe = "".join(ch for ch in str(session or "default") if ch.isalnum() or ch in "-_")
    return os.path.join(folder, f"deck_guard_{safe}.json")


def load_state(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"decks": [], "stop_blocks": 0}


def save_state(path, state):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f)


# --- CLI mode ---------------------------------------------------------------

def cli_mode(args):
    root = project_root()
    decks = args if args else all_deck_files(root)
    if not decks:
        print(f"No decks found in {os.path.join(root, DECKS_DIR)}.")
        return 0
    failed = False
    for deck in decks:
        code, output = run_checker(root, deck)
        label = os.path.relpath(deck, root)
        if code != 0:
            failed = True
            print(f"FAIL  {label}\n{output}\n")
        else:
            print(f"PASS  {label}")
    print("\nFAIL" if failed else "\nPASS")
    return 1 if failed else 0


# --- Claude Code hook mode --------------------------------------------------

def hook_mode(data):
    root = (os.environ.get("CLAUDE_PROJECT_DIR")
            or data.get("cwd")
            or os.getcwd())
    event = data.get("hook_event_name")
    spath = state_path(root, data.get("session_id"))
    state = load_state(spath)

    if event == "PostToolUse":
        path = (data.get("tool_input") or {}).get("file_path", "")
        if not is_deck_file(root, path):
            return 0
        full = os.path.abspath(os.path.join(root, path))
        if full not in state["decks"]:
            state["decks"].append(full)
            save_state(spath, state)
        code, output = run_checker(root, full)
        if code != 0:
            print(f"check_deck.py failed for {os.path.relpath(full, root)}. "
                  f"Fix these and save again:\n{output}", file=sys.stderr)
            return 2
        return 0

    if event == "Stop":
        failing = []
        for deck in state["decks"]:
            if os.path.exists(deck):
                code, output = run_checker(root, deck)
                if code != 0:
                    failing.append(f"{os.path.relpath(deck, root)}:\n{output}")
        if not failing:
            return 0
        if state.get("stop_blocks", 0) >= MAX_STOP_BLOCKS:
            print("deck_guard: deck still fails after several attempts; stopping anyway.",
                  file=sys.stderr)
            return 0
        state["stop_blocks"] = state.get("stop_blocks", 0) + 1
        save_state(spath, state)
        print("You can't finish yet: AGENTS.md requires every deck to pass check_deck.py "
              "with the full write-up (roles, strategy, main_resource, 3+ synergies, 3 rejected cards).\n\n"
              + "\n\n".join(failing), file=sys.stderr)
        return 2

    return 0


def main():
    # Explicit arguments -> CLI mode.
    if len(sys.argv) > 1:
        sys.exit(cli_mode(sys.argv[1:]))

    # No args. A Claude Code hook pipes its event JSON in on stdin; anything
    # else (a terminal, CI, or an empty stdin) means "check every deck".
    if not sys.stdin.isatty():
        raw = sys.stdin.read()
        if raw.strip():
            try:
                data = json.loads(raw)
            except ValueError:
                data = None
            if isinstance(data, dict) and data.get("hook_event_name"):
                sys.exit(hook_mode(data))

    sys.exit(cli_mode([]))


if __name__ == "__main__":
    main()
