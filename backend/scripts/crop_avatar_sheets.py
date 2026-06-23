"""Crop generated avatar sheets into transparent PNG avatar assets.

Expected input sheets:
- 4x4 grid
- chroma magenta background
- no cell frames

The script flood-fills the magenta background from each cell edge, trims the
portrait, normalizes it into a square canvas, and exports 192/128/64 previews.
"""

from __future__ import annotations

import argparse
from collections import deque
from pathlib import Path

from PIL import Image, ImageDraw


def is_chroma_bg(pixel: tuple[int, int, int, int]) -> bool:
    r, g, b, _ = pixel
    # Keep this strict enough to avoid deleting purple goalkeeper shirts.
    # The generated sheets use a high-saturation magenta screen color; dark
    # purple kit pixels should not satisfy these channel thresholds.
    return r > 115 and b > 115 and g < 145 and r > g + 45 and b > g + 45


def flood_key(cell: Image.Image) -> Image.Image:
    cell = cell.convert("RGBA")
    pix = cell.load()
    width, height = cell.size
    seen: set[tuple[int, int]] = set()
    queue: deque[tuple[int, int]] = deque()

    for x in range(width):
        queue.append((x, 0))
        queue.append((x, height - 1))
    for y in range(height):
        queue.append((0, y))
        queue.append((width - 1, y))

    while queue:
        x, y = queue.popleft()
        if x < 0 or y < 0 or x >= width or y >= height or (x, y) in seen:
            continue
        seen.add((x, y))
        if not is_chroma_bg(pix[x, y]):
            continue
        pix[x, y] = (0, 0, 0, 0)
        queue.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))

    return cell


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


def remove_magenta_fringe(image: Image.Image) -> Image.Image:
    image = image.convert("RGBA")
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
    return image


def remove_stray_components(cell: Image.Image) -> Image.Image:
    """Keep the avatar body and discard fragments from neighboring cells."""
    cell = cell.convert("RGBA")
    pix = cell.load()
    width, height = cell.size
    seen: set[tuple[int, int]] = set()
    components: list[tuple[list[tuple[int, int]], tuple[int, int, int, int]]] = []

    for start_y in range(height):
        for start_x in range(width):
            if (start_x, start_y) in seen or pix[start_x, start_y][3] == 0:
                continue

            queue: deque[tuple[int, int]] = deque([(start_x, start_y)])
            component: list[tuple[int, int]] = []
            seen.add((start_x, start_y))
            while queue:
                x, y = queue.popleft()
                component.append((x, y))
                for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
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

            xs = [point[0] for point in component]
            ys = [point[1] for point in component]
            components.append((component, (min(xs), min(ys), max(xs), max(ys))))

    if not components:
        return cell

    main_component, main_bbox = max(components, key=lambda item: len(item[0]))
    main_left, main_top, main_right, main_bottom = main_bbox
    main_area = len(main_component)

    keep: set[int] = set()
    for index, (component, bbox) in enumerate(components):
        left, top, right, bottom = bbox
        area = len(component)
        center_x = (left + right) / 2
        center_y = (top + bottom) / 2

        near_main = (
            main_left - 42 <= center_x <= main_right + 42
            and main_top - 8 <= center_y <= main_bottom + 34
        )
        above_main = bottom < main_top + 6
        substantial = area >= max(80, main_area * 0.025)
        is_main = bbox == main_bbox and area == main_area

        if is_main or (near_main and substantial and not above_main):
            keep.add(index)

    for index, (component, _) in enumerate(components):
        if index in keep:
            continue
        for x, y in component:
            pix[x, y] = (0, 0, 0, 0)

    return cell


def normalize_avatar(cell: Image.Image, canvas_size: int) -> Image.Image:
    bbox = cell.getbbox()
    trimmed = cell.crop(bbox) if bbox else cell
    square = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))

    # Slightly larger than the previous test: bigger heads and wider shoulders.
    max_width = int(canvas_size * 0.965)
    max_height = int(canvas_size * 0.955)
    scale = min(max_width / trimmed.width, max_height / trimmed.height)
    resized = trimmed.resize(
        (round(trimmed.width * scale), round(trimmed.height * scale)),
        Image.Resampling.NEAREST,
    )
    square.alpha_composite(
        resized,
        ((canvas_size - resized.width) // 2, canvas_size - resized.height - 4),
    )
    return square


def crop_sheet(
    sheet_path: Path,
    out_dir: Path,
    prefix: str,
    start_index: int,
    cols: int,
    rows: int,
) -> list[Image.Image]:
    image = Image.open(sheet_path).convert("RGBA")
    width, height = image.size
    avatars: list[Image.Image] = []

    out_dir.mkdir(parents=True, exist_ok=True)
    for row in range(rows):
        for col in range(cols):
            idx = start_index + row * cols + col
            left = round(col * width / cols)
            right = round((col + 1) * width / cols)
            top = round(row * height / rows)
            bottom = round((row + 1) * height / rows)
            raw_cell = image.crop(
                (
                    left,
                    top,
                    right,
                    bottom,
                )
            )
            keyed = remove_stray_components(flood_key(raw_cell))
            avatar_192 = remove_magenta_fringe(normalize_avatar(keyed, 192))
            avatar_128 = avatar_192.resize((128, 128), Image.Resampling.NEAREST)
            avatar_64 = avatar_192.resize((64, 64), Image.Resampling.NEAREST)

            avatar_192.save(out_dir / f"{prefix}_{idx:03d}_192.png")
            avatar_128.save(out_dir / f"{prefix}_{idx:03d}_128.png")
            avatar_64.save(out_dir / f"{prefix}_{idx:03d}.png")
            avatars.append(avatar_192)

    return avatars


def write_preview(avatars: list[Image.Image], out_path: Path) -> None:
    cell = 192
    cols = 8
    rows = (len(avatars) + cols - 1) // cols
    sheet = Image.new("RGBA", (cols * cell, rows * cell), (0, 0, 0, 0))
    draw = ImageDraw.Draw(sheet)
    for y in range(0, rows * cell, 16):
        for x in range(0, cols * cell, 16):
            fill = (28, 32, 38, 255) if ((x // 16 + y // 16) % 2) else (14, 17, 22, 255)
            draw.rectangle((x, y, x + 15, y + 15), fill=fill)
    for index, avatar in enumerate(avatars):
        sheet.alpha_composite(avatar, ((index % cols) * cell, (index // cols) * cell))
    sheet.save(out_path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sheets", nargs="+", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--cols", type=int, default=4)
    parser.add_argument("--rows", type=int, default=4)
    parser.add_argument("--start-index", type=int, default=1)
    args = parser.parse_args()

    all_avatars: list[Image.Image] = []
    start_index = args.start_index
    for sheet in args.sheets:
        avatars = crop_sheet(sheet, args.out, args.prefix, start_index, args.cols, args.rows)
        all_avatars.extend(avatars)
        start_index += len(avatars)

    write_preview(all_avatars, args.out / f"{args.prefix}_preview_checker.png")
    print(args.out / f"{args.prefix}_preview_checker.png")


if __name__ == "__main__":
    main()
