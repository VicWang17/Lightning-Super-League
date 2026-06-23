"""Audit transparent avatar PNG assets for crop/keying defects."""

from __future__ import annotations

import argparse
from collections import deque
from pathlib import Path

from PIL import Image, ImageDraw


def is_magenta_residue(pixel: tuple[int, int, int, int]) -> bool:
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


def components(image: Image.Image) -> list[tuple[int, tuple[int, int, int, int]]]:
    pix = image.load()
    width, height = image.size
    seen: set[tuple[int, int]] = set()
    result: list[tuple[int, tuple[int, int, int, int]]] = []

    for y in range(height):
        for x in range(width):
            if (x, y) in seen or pix[x, y][3] == 0:
                continue
            queue: deque[tuple[int, int]] = deque([(x, y)])
            seen.add((x, y))
            xs: list[int] = []
            ys: list[int] = []
            area = 0
            while queue:
                cx, cy = queue.popleft()
                xs.append(cx)
                ys.append(cy)
                area += 1
                for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                    if (
                        nx < 0
                        or ny < 0
                        or nx >= width
                        or ny >= height
                        or (nx, ny) in seen
                        or pix[nx, ny][3] == 0
                    ):
                        continue
                    seen.add((nx, ny))
                    queue.append((nx, ny))
            result.append((area, (min(xs), min(ys), max(xs), max(ys))))
    return sorted(result, reverse=True)


def audit_file(path: Path) -> list[str]:
    image = Image.open(path).convert("RGBA")
    width, height = image.size
    pix = image.load()
    issues: list[str] = []

    magenta_count = 0
    opaque_count = 0
    bad_edge_count = 0
    for y in range(height):
        for x in range(width):
            pixel = pix[x, y]
            if pixel[3] > 0:
                opaque_count += 1
                # Bottom edge often contains normal shirt pixels after square
                # normalization. Only top/side contact usually indicates a bad
                # crop or neighboring-cell fragment.
                if x <= 1 or y <= 1 or x >= width - 2:
                    bad_edge_count += 1
                if is_magenta_residue(pixel):
                    magenta_count += 1

    if magenta_count >= 8:
        issues.append(f"magenta_residue={magenta_count}")
    if bad_edge_count >= 8:
        issues.append(f"side_or_top_edge_touch={bad_edge_count}")
    if opaque_count < width * height * 0.16:
        issues.append(f"too_sparse={opaque_count}")
    if opaque_count > width * height * 0.82:
        issues.append(f"too_dense={opaque_count}")

    comps = components(image)
    if comps:
        main_area, main_bbox = comps[0]
        main_left, main_top, main_right, main_bottom = main_bbox
        for area, bbox in comps[1:]:
            left, top, right, bottom = bbox
            center_x = (left + right) / 2
            center_y = (top + bottom) / 2
            near_main = (
                main_left - 8 <= center_x <= main_right + 8
                and main_top - 8 <= center_y <= main_bottom + 8
            )
            if area >= max(14, main_area * 0.01) and not near_main:
                issues.append(f"stray_component={area}@{bbox}")
                break

    return issues


def write_contact_sheet(paths: list[Path], out_path: Path) -> None:
    if not paths:
        return
    cell = 96
    cols = 8
    rows = (len(paths) + cols - 1) // cols
    sheet = Image.new("RGBA", (cols * cell, rows * cell), (0, 0, 0, 0))
    draw = ImageDraw.Draw(sheet)
    for y in range(0, rows * cell, 8):
        for x in range(0, cols * cell, 8):
            fill = (28, 32, 38, 255) if ((x // 8 + y // 8) % 2) else (14, 17, 22, 255)
            draw.rectangle((x, y, x + 7, y + 7), fill=fill)
    for index, path in enumerate(paths):
        image = Image.open(path).convert("RGBA").resize((64, 64), Image.Resampling.NEAREST)
        x = (index % cols) * cell + 16
        y = (index // cols) * cell + 6
        sheet.alpha_composite(image, (x, y))
        draw.text((index % cols * cell + 4, y + 68), path.stem[-7:], fill=(230, 230, 230, 255))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--preview", type=Path)
    args = parser.parse_args()

    files: list[Path] = []
    for path in args.paths:
        if path.is_dir():
            files.extend(sorted(path.glob("*.png")))
        else:
            files.append(path)

    failed: list[Path] = []
    for file in files:
        issues = audit_file(file)
        if issues:
            failed.append(file)
            print(f"{file}: {', '.join(issues)}")

    print(f"checked={len(files)} failed={len(failed)}")
    if args.preview:
        write_contact_sheet(failed[:128], args.preview)


if __name__ == "__main__":
    main()
