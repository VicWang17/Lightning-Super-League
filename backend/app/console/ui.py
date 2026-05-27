from __future__ import annotations

import os
import sys
from dataclasses import dataclass


class C:
    BOLD = "\033[1m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    DIM = "\033[2m"
    END = "\033[0m"


@dataclass(frozen=True)
class MenuItem:
    key: str
    label: str
    hint: str = ""
    aliases: tuple[str, ...] = ()
    highlight: bool = False


def clear_screen() -> None:
    if sys.stdout.isatty():
        os.system("clear")


def header(title: str, subtitle: str = "") -> None:
    clear_screen()
    print(f"{C.BOLD}{C.CYAN}{title}{C.END}")
    if subtitle:
        print(f"{C.DIM}{subtitle}{C.END}")
    print("=" * 78)


def menu(title: str, items: list[MenuItem], footer: str = "") -> str:
    header(title)
    for item in items:
        line = f"  {item.key:<8} {item.label}"
        if item.hint:
            line += f"  {C.DIM}{item.hint}{C.END}"
        if item.highlight:
            line = f"{C.GREEN}{line}{C.END}"
        print(line)
    print("-" * 78)
    if footer:
        print(footer)
        print("-" * 78)
    return input("选择 > ").strip().lower()


def pause() -> None:
    input(f"\n{C.DIM}按回车继续...{C.END}")


def success(text: str) -> None:
    print(f"{C.GREEN}ok: {text}{C.END}")


def warning(text: str) -> None:
    print(f"{C.YELLOW}warn: {text}{C.END}")


def error(text: str) -> None:
    print(f"{C.RED}error: {text}{C.END}")


def section(text: str) -> None:
    print(f"\n{C.BOLD}{C.CYAN}== {text}{C.END}")


def ask_float(prompt: str, default: float) -> float:
    raw = input(f"{prompt} [{default:g}] > ").strip()
    return float(raw) if raw else default


def ask_int(prompt: str, default: int) -> int:
    raw = input(f"{prompt} [{default}] > ").strip()
    return int(raw) if raw else default


def ask_yes_no(prompt: str, default: bool = False) -> bool:
    suffix = "Y/n" if default else "y/N"
    raw = input(f"{prompt} ({suffix}) > ").strip().lower()
    if not raw:
        return default
    return raw in {"y", "yes"}


def progress_bar(value: float, width: int) -> str:
    value = max(0.0, min(1.0, value))
    filled = int(value * width)
    return "[" + "#" * filled + "-" * (width - filled) + "]"


def format_counts(counts: dict) -> str:
    return " ".join(f"{key}={value}" for key, value in counts.items()) or "none"
