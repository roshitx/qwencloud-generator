#!/usr/bin/env python3
"""Tiny colored terminal logger."""
import shutil
import sys


class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    ORANGE = "\033[38;5;208m"


def _color(text: str, color: str) -> str:
    return f"{color}{text}{C.RESET}"


def bold(text: str) -> str:
    return _color(text, C.BOLD)


def dim(text: str) -> str:
    return _color(text, C.DIM)


def red(text: str) -> str:
    return _color(text, C.RED)


def green(text: str) -> str:
    return _color(text, C.GREEN)


def yellow(text: str) -> str:
    return _color(text, C.YELLOW)


def blue(text: str) -> str:
    return _color(text, C.BLUE)


def cyan(text: str) -> str:
    return _color(text, C.CYAN)


def magenta(text: str) -> str:
    return _color(text, C.MAGENTA)


def orange(text: str) -> str:
    return _color(text, C.ORANGE)


def tag(label: str, color: str) -> str:
    return _color(f"[{label}]", color + C.BOLD)


def info(msg: str):
    print(f"{tag('INFO', C.CYAN)} {msg}", file=sys.stderr, flush=True)


def ok(msg: str):
    print(f"{tag(' OK ', C.GREEN)} {msg}", file=sys.stderr, flush=True)


def warn(msg: str):
    print(f"{tag('WARN', C.YELLOW)} {msg}", file=sys.stderr, flush=True)


def error(msg: str):
    print(f"{tag('ERR ', C.RED)} {msg}", file=sys.stderr, flush=True)


def step(idx: int, total: int, msg: str):
    prog = f"[{idx}/{total}]"
    print(f"{dim(prog)} {msg}", file=sys.stderr, flush=True)


def result(status: str, email: str, detail: str = "") -> str:
    mapping = {
        "success": ("SUCCESS", C.GREEN, "✓"),
        "success-no-key": ("NO KEY", C.YELLOW, "⚠"),
        "rate-limited": ("RATE LIMIT", C.YELLOW, "⏳"),
        "access-denied": ("ACCESS DENIED", C.ORANGE, "🚫"),
        "wrong-password": ("WRONG PASS", C.RED, "✕"),
        "locked": ("LOCKED", C.MAGENTA, "🔒"),
        "cf-blocked": ("CF BLOCK", C.ORANGE, "☁"),
        "already-registered": ("ALREADY REG", C.BLUE, "◉"),
        "email-format-rejected": ("BAD EMAIL", C.YELLOW, "✕"),
        "proxy-dead": ("PROXY DEAD", C.RED, "✕"),
        "stuck": ("STUCK", C.YELLOW, "⌛"),
        "timeout": ("TIMEOUT", C.YELLOW, "⌛"),
        "error": ("ERROR", C.RED, "✕"),
    }
    label, color, icon = mapping.get(status, (status.upper(), C.WHITE, "?"))
    detail = f" {dim(detail)}" if detail else ""
    return f"{icon} {tag(label, color)} {cyan(email)}{detail}"


def banner(name: str = "QwenCloud", subtitle: str = "Gmail alias signup + token helper"):
    width = min(shutil.get_terminal_size().columns, 60)
    line = "━" * width
    print()
    print(cyan(line))
    print(f"  {bold(cyan(name))} {bold(white('Account Auto-Register'))}")
    print(dim(f"  {subtitle}"))
    print(cyan(line))
    print()


def summary(success: int, target: int, skipped: int, total: int):
    print()
    print(cyan("━" * 40))
    print(f"  {bold('SUMMARY')}")
    print(f"    {green('✓ Success:')} {green(str(success))}/{target}")
    print(f"    {yellow('⏳ Retries/Errors:')} {yellow(str(total - success - skipped))}")
    print(f"    {blue('◉ Skipped:')} {blue(str(skipped))}")
    print(f"    {dim('◌ Total processed:')} {dim(str(total))}")
    print(cyan("━" * 40))
    print()


def white(text: str) -> str:
    return _color(text, C.WHITE)
