"""Repair existing transparent avatar PNGs by removing magenta key fringes."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image


def is_magenta_fringe(pixel: tuple[int, int, int, int]) -> bool:
    r, g, b, a = pixel
    if a == 0:
        return False

    bright_key = r > 125 and b > 125 and g < 110 and r > g + 45 and b > g + 45
    dark_key_bleed = (
        r > 75
        and b > 75
        and g < 55
        and r > g + 55
        and b > g + 55
        and abs(r - b) < 70
    )
    return bright_key or dark_key_bleed


def repair_image(path: Path) -> int:
    image = Image.open(path).convert("RGBA")
    pix = image.load()
    width, height = image.size
    to_clear: list[tuple[int, int]] = []
    to_despill: list[tuple[int, int]] = []

    for y in range(height):
        for x in range(width):
            if not is_magenta_fringe(pix[x, y]):
                continue
            adjacent_transparent = False
            for nx in range(max(0, x - 1), min(width, x + 2)):
                for ny in range(max(0, y - 1), min(height, y + 2)):
                    if pix[nx, ny][3] == 0:
                        adjacent_transparent = True
                        break
                if adjacent_transparent:
                    break
            if adjacent_transparent:
                to_clear.append((x, y))

    for x, y in to_clear:
        pix[x, y] = (0, 0, 0, 0)

    for y in range(height):
        for x in range(width):
            r, g, b, a = pix[x, y]
            if a == 0 or y > height * 0.82:
                continue
            magenta_bleed = (
                r > 60
                and b > 60
                and g < 65
                and r > g + 32
                and b > g + 32
                and abs(r - b) < 95
            )
            if not magenta_bleed:
                continue
            near_cutout = False
            for nx in range(max(0, x - 2), min(width, x + 3)):
                for ny in range(max(0, y - 2), min(height, y + 3)):
                    if pix[nx, ny][3] == 0:
                        near_cutout = True
                        break
                if near_cutout:
                    break
            if near_cutout:
                to_despill.append((x, y))

    for x, y in to_despill:
        pix[x, y] = (18, 16, 20, 255)

    changed = len(to_clear) + len(to_despill)
    if changed:
        image.save(path)
    return changed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()

    total_files = 0
    total_pixels = 0
    for path in args.paths:
        files = sorted(path.glob("*.png")) if path.is_dir() else [path]
        for file in files:
            changed = repair_image(file)
            total_files += 1
            total_pixels += changed
            if changed:
                print(f"{file}: cleared={changed}")
    print(f"checked={total_files} cleared_pixels={total_pixels}")


if __name__ == "__main__":
    main()
