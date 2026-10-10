"""Render Grit's finite profile intro and static cover with Pillow.

Usage: python scripts/build_profile_art.py [--font-dir PATH]
Requires Pillow. Windows Segoe UI/Consolas or system DejaVu Sans fonts.
The geometry is sampled from the existing Grit SVG, not a replacement mark.
The GIF has no looping extension: it plays once and retains its final frame.
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "profile"
WIDTH, HEIGHT, SCALE = 1120, 520, 2
BG = (17, 24, 27)
INK = (240, 239, 227)
MUTED = (168, 182, 177)
ACCENT = (206, 224, 145)
GHOST = (48, 63, 62)


def fonts(directory: Path | None):
    candidates = [directory] if directory else [
        Path("C:/Windows/Fonts"),
        Path("/usr/share/fonts/truetype/dejavu"),
        Path("/usr/local/share/fonts"),
    ]
    for folder in candidates:
        if folder is None:
            continue
        if (folder / "segoeuib.ttf").exists():
            return folder / "segoeuib.ttf", folder / "segoeui.ttf", folder / "consola.ttf"
        if (folder / "DejaVuSans-Bold.ttf").exists():
            return folder / "DejaVuSans-Bold.ttf", folder / "DejaVuSans.ttf", folder / "DejaVuSansMono.ttf"
    raise SystemExit("Supported fonts not found; pass --font-dir with Segoe UI or DejaVu fonts.")


def tile_polygon(path: str):
    n = list(map(float, re.findall(r"[-+]?(?:\d*\.\d+|\d+)", path)))
    assert len(n) == 18, "Unexpected SVG path; inspect the brand source before regenerating."
    result = []
    for start, end, radius, clockwise in [
        ((n[0], n[1]), (n[7], n[8]), n[2], True),
        ((n[9], n[10]), (n[16], n[17]), n[11], False),
    ]:
        a = math.atan2(start[1] - 64, start[0] - 64)
        b = math.atan2(end[1] - 64, end[0] - 64)
        if clockwise:
            while b < a:
                b += 2 * math.pi
        else:
            while b > a:
                b -= 2 * math.pi
        for i in range(41):
            angle = a + (b - a) * i / 40
            result.append((64 + radius * math.cos(angle), 64 + radius * math.sin(angle)))
    return result


def mix(a, b, amount):
    return tuple(round(x + (y - x) * amount) for x, y in zip(a, b))


def ease(value):
    value = max(0.0, min(1.0, value))
    return 1 - (1 - value) ** 3


def render(progress, polygons, font_paths):
    image = Image.new("RGB", (WIDTH * SCALE, HEIGHT * SCALE), BG)
    d = ImageDraw.Draw(image)

    def line(points, color, width=1):
        d.line([(int(x * SCALE), int(y * SCALE)) for x, y in points], fill=color, width=width * SCALE)

    def text(x, y, value, size, font, color=INK):
        d.text((x * SCALE, y * SCALE), value, font=ImageFont.truetype(str(font), size * SCALE), fill=color)

    bold, regular, mono = font_paths
    line([(56, 67), (84, 67)], ACCENT, 3)
    text(99, 51, "BUILD / CHECK / DELIVER", 20, mono, MUTED)
    text(50, 126, "GRIT", 144, bold)
    text(59, 302, "AI systems.", 33, regular)
    text(59, 346, "Checked work.", 33, regular)
    line([(56, 440), (1064, 440)], GHOST)
    text(58, 461, "ANKARA, TÜRKİYE", 17, mono, MUTED)
    text(756, 461, "OPEN SOURCE / APPLIED AI", 17, mono, MUTED)

    # Quiet technical guides frame the source mark without changing its geometry.
    cx, cy, mark_size = 870, 252, 290
    radius = 172
    d.ellipse(((cx - radius) * SCALE, (cy - radius) * SCALE,
               (cx + radius) * SCALE, (cy + radius) * SCALE), outline=GHOST, width=SCALE)
    for x, y, dx, dy in [(cx - 186, cy, 12, 0), (cx + 174, cy, 12, 0),
                          (cx, cy - 186, 0, 12), (cx, cy + 174, 0, 12)]:
        line([(x, y), (x + dx, y + dy)], MUTED)

    # Four inner tiles, then eight middle tiles, then eight outer tiles assemble.
    order = list(range(16, 20)) + list(range(8, 16)) + list(range(8))
    for index, polygon in enumerate(polygons):
        step = order.index(index)
        phase = ease((progress - step * 0.025) / 0.42)
        color = mix(GHOST, INK, phase)
        shift = (1 - phase) * 13
        points = []
        for x, y in polygon:
            angle = math.atan2(y - 64, x - 64)
            px = cx + (x - 64) * mark_size / 128 + math.cos(angle) * shift
            py = cy + (y - 64) * mark_size / 128 + math.sin(angle) * shift
            points.append((round(px * SCALE), round(py * SCALE)))
        d.polygon(points, fill=color)

    # One small centre light settles with the completed mark; no fake status UI.
    centre = mix(GHOST, ACCENT, ease((progress - 0.75) / 0.25))
    d.ellipse(((cx - 4) * SCALE, (cy - 4) * SCALE,
               (cx + 4) * SCALE, (cy + 4) * SCALE), fill=centre)
    return image.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--font-dir", type=Path)
    args = parser.parse_args()
    source = ET.parse(ROOT / "assets" / "brand" / "grit-disk-mark-white.svg")
    polygons = [tile_polygon(path.attrib["d"]) for path in source.iter("{http://www.w3.org/2000/svg}path")]
    assert len(polygons) == 20
    font_paths = fonts(args.font_dir)
    OUT.mkdir(parents=True, exist_ok=True)
    static = render(1.0, polygons, font_paths)
    static.save(OUT / "grit-cover.png", optimize=True)
    palette = static.quantize(colors=96, method=Image.Quantize.MEDIANCUT)
    frames = [render(i / 47, polygons, font_paths).quantize(palette=palette, dither=Image.Dither.NONE) for i in range(48)]
    frames[0].save(OUT / "grit-intro.gif", save_all=True, append_images=frames[1:],
                   duration=[60] * 47 + [2000], disposal=1, optimize=True)
    for path in (OUT / "grit-cover.png", OUT / "grit-intro.gif"):
        with Image.open(path) as decoded:
            print(f"{path.relative_to(ROOT)}: {decoded.size}, {getattr(decoded, 'n_frames', 1)} frames, {path.stat().st_size} bytes, loop={decoded.info.get('loop', 'absent (plays once)')}")


if __name__ == "__main__":
    main()
