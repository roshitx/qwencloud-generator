#!/usr/bin/env python3
"""Modern TUI dashboard for QwenCloud account harvester.

Uses raw ANSI escape sequences — no external libraries.
Renders a fixed-height frame that updates in-place via cursor movement.
"""
import os
import sys
import time
import threading

# ANSI escape codes
ALT_ENTER = "\033[?1049h"
ALT_EXIT = "\033[?1049l"
HIDE_CURSOR = "\033[?25l"
SHOW_CURSOR = "\033[?25h"
CLEAR = "\033[2J"
HOME = "\033[H"
CLEAR_LINE = "\033[K"
SAVE_CURSOR = "\033[s"
RESTORE_CURSOR = "\033[u"

# Colors
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

SPINNER = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

STATUS_COLORS = {
    "RUNNING": CYAN,
    "SUCCESS": GREEN,
    "FAILED": RED,
    "BURNT": YELLOW,
    "INFO": WHITE,
    "PENDING": DIM,
}


def mask_email(email: str) -> str:
    """Mask email: odin****@gmail.com style (first 4 chars + asterisks)."""
    if "@" not in email:
        return email
    local, domain = email.split("@", 1)
    if len(local) <= 4:
        return local + "****@" + domain
    return local[:4] + "****@" + domain


def mask_key(key: str) -> str:
    """Mask API key: sk-xxx...yyy style."""
    if len(key) > 20:
        return key[:10] + "..." + key[-6:]
    return key


class TUI:
    def __init__(self, target: int, total_emails: int, total_proxies: int,
                 n_threads: int, headless: bool, censor: bool, verbose: bool):
        self.target = target
        self.total_emails = total_emails
        self.total_proxies = total_proxies
        self.n_threads = n_threads
        self.headless = headless
        self.censor = censor
        self.verbose = verbose

        self.start_time = time.time()
        self.lock = threading.Lock()

        # Stats
        self.success = 0
        self.failed = 0
        self.burnt = 0
        self.retry = 0
        self.attempted = 0
        self.remaining_proxies = total_proxies

        # Worker states
        self.workers = {}
        for i in range(1, n_threads + 1):
            self.workers[i] = {
                "status": "IDLE",
                "email": "",
                "detail": "",
                "elapsed": 0,
                "start": 0,
            }

        # Render control
        self._running = False
        self._render_thread = None
        self._spinner_idx = 0
        self._frame_count = 0
        self._last_render = ""

    def start(self):
        """Enter alternate screen and start render loop."""
        sys.stdout.write(ALT_ENTER + HIDE_CURSOR + CLEAR + HOME)
        sys.stdout.flush()
        self._running = True
        self._render_thread = threading.Thread(target=self._render_loop, daemon=True)
        self._render_thread.start()

    def stop(self):
        """Exit alternate screen and clean up."""
        self._running = False
        if self._render_thread:
            self._render_thread.join(timeout=2)
        sys.stdout.write(SHOW_CURSOR + ALT_EXIT + "\033[2J\033[H")
        sys.stdout.flush()
        self._render_thread = None

    def update_worker_done(self, wid: int):
        """Mark a worker as done/idle after finishing."""
        with self.lock:
            if wid in self.workers:
                self.workers[wid]["status"] = "IDLE"
                self.workers[wid]["detail"] = "done"

    def update_worker(self, wid: int, status: str, email: str = "", detail: str = "", elapsed: float = 0):
        """Update a worker's state (thread-safe)."""
        with self.lock:
            if wid not in self.workers:
                self.workers[wid] = {"status": "IDLE", "email": "", "detail": "", "elapsed": 0, "start": 0}
            display = mask_email(email) if self.censor and email else email
            self.workers[wid]["status"] = status
            self.workers[wid]["email"] = display
            self.workers[wid]["detail"] = detail
            self.workers[wid]["elapsed"] = elapsed
            if status == "RUNNING" and elapsed == 0:
                self.workers[wid]["start"] = time.time()

    def update_stats(self, success: int = None, failed: int = None, burnt: int = None,
                     retry: int = None, attempted: int = None, remaining_proxies: int = None):
        """Update global stats (thread-safe, increment if value is int)."""
        with self.lock:
            if success is not None:
                self.success = success
            if failed is not None:
                self.failed = failed
            if burnt is not None:
                self.burnt = burnt
            if retry is not None:
                self.retry = retry
            if attempted is not None:
                self.attempted = attempted
            if remaining_proxies is not None:
                self.remaining_proxies = remaining_proxies

    def _get_cpu_mem(self):
        """Get CPU% and memory usage on Linux."""
        try:
            # CPU usage (quick read of /proc/stat)
            with open("/proc/stat") as f:
                cpu1 = f.readline().split()[1:]
            cpu1_total = sum(int(x) for x in cpu1)
            cpu1_idle = int(cpu1[3])
            time.sleep(0.1)
            with open("/proc/stat") as f:
                cpu2 = f.readline().split()[1:]
            cpu2_total = sum(int(x) for x in cpu2)
            cpu2_idle = int(cpu2[3])
            cpu_pct = 100 * (1 - (cpu2_idle - cpu1_idle) / max(cpu2_total - cpu1_total, 1))
        except Exception:
            cpu_pct = 0

        try:
            # Memory usage
            with open("/proc/meminfo") as f:
                lines = f.readlines()
            mem_total = int(lines[0].split()[1])
            mem_avail = int(lines[2].split()[1])
            mem_used = mem_total - mem_avail
            mem_pct = 100 * mem_used / mem_total
            mem_str = f"{mem_used // 1024}MB"
        except Exception:
            mem_pct = 0
            mem_str = "?"

        return cpu_pct, mem_pct, mem_str

    def _render_loop(self):
        """Background render loop at ~10 FPS."""
        while self._running:
            self._render()
            time.sleep(0.1)

    def _render(self):
        """Render the full frame using cursor movement (diff-like)."""
        with self.lock:
            now = time.time()
            elapsed = now - self.start_time
            self._spinner_idx = (self._spinner_idx + 1) % len(SPINNER)
            spinner = SPINNER[self._spinner_idx]

            # Get terminal size
            try:
                term_h, term_w = os.get_terminal_size()
            except Exception:
                term_h, term_w = 24, 80

            # Calculate TPS and ETA
            if self.success > 0 and elapsed > 0:
                tps = self.success / elapsed
                remaining = self.target - self.success
                eta_sec = remaining / tps if tps > 0 else 0
                eta_str = f"{int(eta_sec // 60)}m{int(eta_sec % 60)}s"
                rate = f"{tps * 60:.1f}/min"
            else:
                eta_str = "—"
                rate = "—"

            success_pct = (self.success / self.target * 100) if self.target > 0 else 0
            running = sum(1 for w in self.workers.values() if w["status"] == "RUNNING")

            # CPU/Mem (sampled every 10 frames to reduce overhead)
            if self._frame_count % 10 == 0:
                self._cpu, self._mem_pct, self._mem_str = self._get_cpu_mem()
            self._frame_count += 1
            cpu = getattr(self, "_cpu", 0)
            mem_pct = getattr(self, "_mem_pct", 0)
            mem_str = getattr(self, "_mem_str", "?")

            # Build frame
            lines = []
            w = min(term_w - 2, 76)

            # Title bar
            lines.append(f"{CYAN}{BOLD}┌{'─' * w}┐{RESET}")
            lines.append(
                f"{CYAN}{BOLD}│{RESET} "
                f"{CYAN}{BOLD}QwenCloud Harvester{RESET}"
                f"  {DIM}│ Emails: {WHITE}{BOLD}{self.total_emails}{RESET}"
                f" {DIM}│ Proxies: {WHITE}{BOLD}{self.remaining_proxies}{RESET}"
                f" {DIM}│ Threads: {WHITE}{BOLD}{self.n_threads}{RESET}"
                f" {DIM}│ {'HIDDEN' if self.headless else 'VISIBLE'}"
                f"{' ' * 3}{CYAN}{BOLD}│{RESET}"
            )

            # Progress bar
            bar_len = min(w - 30, 40)
            filled = int(bar_len * success_pct / 100)
            bar = "█" * filled + "░" * (bar_len - filled)
            lines.append(f"{CYAN}{BOLD}├{'─' * w}┤{RESET}")
            lines.append(
                f"{CYAN}{BOLD}│{RESET} "
                f"Progress: {GREEN}{bar}{RESET} "
                f"{self.success}/{self.target} ({success_pct:.0f}%)"
                f"{' ' * max(1, w - 30 - len(bar))}{CYAN}{BOLD}│{RESET}"
            )

            # Stats line
            lines.append(
                f"{CYAN}{BOLD}│{RESET} "
                f"{GREEN}✓ Success: {BOLD}{self.success}{RESET}  "
                f"{RED}✕ Failed: {BOLD}{self.failed}{RESET}  "
                f"{YELLOW}⚠ Burnt: {BOLD}{self.burnt}{RESET}  "
                f"{CYAN}● Running: {BOLD}{running}{RESET}  "
                f"{ORANGE}↻ Retry: {BOLD}{self.retry}{RESET}"
                f"{' ' * 8}{CYAN}{BOLD}│{RESET}"
            )
            lines.append(f"{CYAN}{BOLD}└{'─' * w}┘{RESET}")

            # Empty line
            lines.append("")

            # Worker rows — paginate if terminal too small
            header_lines = 7  # title + progress + stats + box + empty
            footer_lines = 3   # separator + footer + empty
            available = term_h - header_lines - footer_lines
            visible_workers = min(self.n_threads, max(1, available))

            for i in range(1, visible_workers + 1):
                ws = self.workers.get(i, {"status": "IDLE", "email": "", "detail": "", "elapsed": 0, "start": 0})
                status = ws["status"]
                color = STATUS_COLORS.get(status, WHITE)

                if status == "RUNNING":
                    w_elapsed = time.time() - ws.get("start", time.time())
                    spin = spinner
                else:
                    w_elapsed = ws.get("elapsed", 0)
                    spin = " "

                email_display = ws.get("email", "")
                detail = ws.get("detail", "")
                if detail:
                    detail_display = f"  {DIM}{detail[:20]}{RESET}"
                else:
                    detail_display = ""

                lines.append(
                    f" {DIM}[W{i}]{RESET} "
                    f"{color}{BOLD}{spin} {status:<8}{RESET} "
                    f"{WHITE}{email_display:<25}{RESET}"
                    f"{detail_display}"
                    f"{DIM}{w_elapsed:>6.1f}s{RESET}"
                )

            # If more workers than visible, show paging indicator
            if visible_workers < self.n_threads:
                lines.append(f" {DIM}... {self.n_threads - visible_workers} more workers (resize terminal to see){RESET}")

            # Footer
            lines.append("")
            lines.append(f"{DIM}{'─' * (w + 2)}{RESET}")
            lines.append(
                f" {CYAN}ETA: {BOLD}{eta_str}{RESET}"
                f"  {DIM}│ Rate: {WHITE}{rate}{RESET}"
                f"  {DIM}│ Elapsed: {WHITE}{int(elapsed // 60)}m{int(elapsed % 60)}s{RESET}"
                f"  {DIM}│ CPU: {WHITE}{cpu:.0f}%{RESET}"
                f"  {DIM}│ Mem: {WHITE}{mem_str} ({mem_pct:.0f}%){RESET}"
            )

            # Truncate to terminal height
            max_lines = term_h - 1
            if len(lines) > max_lines:
                lines = lines[:max_lines]

            frame = "\n".join(lines) + "\n"

            # Render: move to home, clear, write
            sys.stdout.write(HOME + CLEAR)
            sys.stdout.write(frame)
            sys.stdout.flush()

    def print_summary(self):
        """Print final summary after TUI closes."""
        elapsed = time.time() - self.start_time
        print(f"\n{CYAN}{'━' * 50}{RESET}")
        print(f"  {BOLD}SUMMARY{RESET}")
        print(f"    {GREEN}✓ Success: {GREEN}{self.success}/{self.target}{RESET}")
        print(f"    {RED}✕ Failed: {self.failed}{RESET}")
        print(f"    {YELLOW}⚠ Burnt: {self.burnt}{RESET}")
        print(f"    {DIM}◌ Attempted: {self.attempted}{RESET}")
        print(f"    {DIM}◌ Elapsed: {int(elapsed // 60)}m{int(elapsed % 60)}s{RESET}")
        if self.success > 0 and elapsed > 0:
            print(f"    {DIM}◌ Rate: {self.success / elapsed * 60:.1f} keys/min{RESET}")
        print(f"{CYAN}{'━' * 50}{RESET}\n")
