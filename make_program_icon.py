#!/usr/bin/env python3
from __future__ import annotations

import math
import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ASSET_DIR = ROOT / "windows-exe-bundle" / "assets"
ASSET_DIR.mkdir(parents=True, exist_ok=True)

BG_TOP = (20, 34, 61, 255)
BG_BOTTOM = (10, 20, 39, 255)
ACCENT = (59, 130, 246, 255)
ACCENT2 = (34, 211, 238, 255)
WHITE = (246, 248, 252, 255)
PAPER = (238, 243, 250, 255)
PAPER_LINE = (176, 197, 225, 255)
SHADOW = (0, 0, 0, 90)

SIZES = [16, 32, 48, 64, 128, 256]


def lerp(a, b, t):
    return a + (b - a) * t


def blend(dst, src):
    sa = src[3] / 255.0
    da = dst[3] / 255.0
    out_a = sa + da * (1 - sa)
    if out_a <= 0:
        return (0, 0, 0, 0)
    out = []
    for i in range(3):
        out_c = (src[i] * sa + dst[i] * da * (1 - sa)) / out_a
        out.append(int(round(out_c)))
    out.append(int(round(out_a * 255)))
    return tuple(out)


def over(img, x, y, color):
    if 0 <= x < len(img[0]) and 0 <= y < len(img):
        img[y][x] = blend(img[y][x], color)


def draw_circle(img, cx, cy, r, color):
    x0 = max(0, int(cx - r - 1))
    x1 = min(len(img[0]), int(cx + r + 2))
    y0 = max(0, int(cy - r - 1))
    y1 = min(len(img), int(cy + r + 2))
    for y in range(y0, y1):
        for x in range(x0, x1):
            dx = x + 0.5 - cx
            dy = y + 0.5 - cy
            d = math.hypot(dx, dy)
            if d <= r:
                over(img, x, y, color)
            elif d <= r + 1:
                a = max(0.0, 1 - (d - r))
                over(img, x, y, (color[0], color[1], color[2], int(color[3] * a)))


def point_in_round_rect(px, py, x, y, w, h, r):
    if x + r <= px <= x + w - r and y <= py <= y + h:
        return True
    if x <= px <= x + w and y + r <= py <= y + h - r:
        return True
    corners = [
        (x + r, y + r),
        (x + w - r, y + r),
        (x + r, y + h - r),
        (x + w - r, y + h - r),
    ]
    for cx, cy in corners:
        if (px - cx) ** 2 + (py - cy) ** 2 <= r ** 2:
            return True
    return False


def draw_round_rect(img, x, y, w, h, r, color):
    x0 = max(0, int(x - 1))
    x1 = min(len(img[0]), int(x + w + 1))
    y0 = max(0, int(y - 1))
    y1 = min(len(img), int(y + h + 1))
    for yy in range(y0, y1):
        for xx in range(x0, x1):
            if point_in_round_rect(xx + 0.5, yy + 0.5, x, y, w, h, r):
                over(img, xx, yy, color)


def draw_polygon(img, points, color):
    min_x = max(0, int(min(p[0] for p in points)) - 1)
    max_x = min(len(img[0]), int(max(p[0] for p in points)) + 2)
    min_y = max(0, int(min(p[1] for p in points)) - 1)
    max_y = min(len(img), int(max(p[1] for p in points)) + 2)
    for y in range(min_y, max_y):
        for x in range(min_x, max_x):
            px, py = x + 0.5, y + 0.5
            inside = False
            j = len(points) - 1
            for i in range(len(points)):
                xi, yi = points[i]
                xj, yj = points[j]
                hit = ((yi > py) != (yj > py)) and (px < (xj - xi) * (py - yi) / ((yj - yi) or 1e-9) + xi)
                if hit:
                    inside = not inside
                j = i
            if inside:
                over(img, x, y, color)


def draw_line(img, x1, y1, x2, y2, thickness, color):
    min_x = max(0, int(min(x1, x2) - thickness - 2))
    max_x = min(len(img[0]), int(max(x1, x2) + thickness + 2))
    min_y = max(0, int(min(y1, y2) - thickness - 2))
    max_y = min(len(img), int(max(y1, y2) + thickness + 2))
    dx = x2 - x1
    dy = y2 - y1
    denom = dx * dx + dy * dy or 1.0
    for y in range(min_y, max_y):
        for x in range(min_x, max_x):
            px, py = x + 0.5, y + 0.5
            t = ((px - x1) * dx + (py - y1) * dy) / denom
            t = max(0.0, min(1.0, t))
            nx = x1 + t * dx
            ny = y1 + t * dy
            dist = math.hypot(px - nx, py - ny)
            if dist <= thickness / 2:
                over(img, x, y, color)
            elif dist <= thickness / 2 + 1:
                a = max(0.0, 1 - (dist - thickness / 2))
                over(img, x, y, (color[0], color[1], color[2], int(color[3] * a)))


def make_canvas(n):
    img = []
    for y in range(n):
        row = []
        t = y / max(1, n - 1)
        base = tuple(int(lerp(BG_TOP[i], BG_BOTTOM[i], t)) for i in range(4))
        for x in range(n):
            row.append(base)
        img.append(row)
    return img


def draw_icon(n):
    img = make_canvas(n)
    pad = n * 0.08
    radius = n * 0.22

    # glow accents
    draw_circle(img, n * 0.78, n * 0.22, n * 0.22, (ACCENT2[0], ACCENT2[1], ACCENT2[2], 42))
    draw_circle(img, n * 0.28, n * 0.8, n * 0.26, (ACCENT[0], ACCENT[1], ACCENT[2], 30))

    # background rounded plate for visual edge
    draw_round_rect(img, pad, pad, n - 2 * pad, n - 2 * pad, radius, (255, 255, 255, 10))

    # shadow for pages
    page_w = n * 0.42
    page_h = n * 0.52
    px = n * 0.24
    py = n * 0.18
    rr = n * 0.05
    draw_round_rect(img, px - n * 0.015, py + n * 0.055, page_w, page_h, rr, SHADOW)
    draw_round_rect(img, px + n * 0.06, py + n * 0.015, page_w, page_h, rr, SHADOW)

    # back page
    draw_round_rect(img, px + n * 0.05, py + n * 0.01, page_w, page_h, rr, PAPER)
    # front page
    draw_round_rect(img, px, py + n * 0.05, page_w, page_h, rr, WHITE)

    # page fold accent
    tri = [
        (px + page_w - n * 0.11, py + n * 0.05),
        (px + page_w, py + n * 0.05),
        (px + page_w, py + n * 0.16),
    ]
    draw_polygon(img, tri, (223, 232, 246, 255))

    # page lines
    for frac in [0.22, 0.34, 0.46, 0.58]:
        y = py + n * 0.05 + page_h * frac
        draw_line(img, px + n * 0.08, y, px + page_w - n * 0.08, y, max(1.2, n * 0.012), PAPER_LINE)

    # accent bookmark
    draw_round_rect(img, px + page_w - n * 0.09, py + n * 0.1, n * 0.045, n * 0.14, n * 0.012, ACCENT2)

    # arrow shadow
    shaft_x = n * 0.67
    shaft_top = n * 0.34
    shaft_bottom = n * 0.64
    thick = n * 0.09
    draw_line(img, shaft_x + n * 0.014, shaft_top + n * 0.02, shaft_x + n * 0.014, shaft_bottom + n * 0.02, thick, SHADOW)
    arrow_shadow = [
        (shaft_x - n * 0.11 + n * 0.014, n * 0.59 + n * 0.02),
        (shaft_x + n * 0.11 + n * 0.014, n * 0.59 + n * 0.02),
        (shaft_x + n * 0.014, n * 0.78 + n * 0.02),
    ]
    draw_polygon(img, arrow_shadow, SHADOW)

    # arrow shaft
    draw_line(img, shaft_x, shaft_top, shaft_x, shaft_bottom, thick, ACCENT)
    # arrow head
    arrow = [
        (shaft_x - n * 0.11, n * 0.59),
        (shaft_x + n * 0.11, n * 0.59),
        (shaft_x, n * 0.78),
    ]
    draw_polygon(img, arrow, ACCENT)

    # top highlight of shaft
    draw_line(img, shaft_x - n * 0.018, shaft_top + n * 0.02, shaft_x - n * 0.018, shaft_bottom - n * 0.03, n * 0.022, ACCENT2)

    # download tray
    tray = [
        (n * 0.52, n * 0.77),
        (n * 0.82, n * 0.77),
        (n * 0.78, n * 0.87),
        (n * 0.56, n * 0.87),
    ]
    draw_polygon(img, tray, (18, 31, 56, 220))
    draw_line(img, n * 0.56, n * 0.87, n * 0.78, n * 0.87, n * 0.03, ACCENT2)

    return img


def png_chunk(tag: bytes, data: bytes) -> bytes:
    return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff)


def encode_png(img):
    h = len(img)
    w = len(img[0])
    raw = bytearray()
    for row in img:
        raw.append(0)
        for r, g, b, a in row:
            raw.extend([r, g, b, a])
    ihdr = struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0)
    return b'\x89PNG\r\n\x1a\n' + png_chunk(b'IHDR', ihdr) + png_chunk(b'IDAT', zlib.compress(bytes(raw), 9)) + png_chunk(b'IEND', b'')


def encode_ico(images):
    count = len(images)
    header = struct.pack('<HHH', 0, 1, count)
    entries = []
    offset = 6 + 16 * count
    blobs = []
    for size, png in images:
        width = 0 if size == 256 else size
        height = 0 if size == 256 else size
        entry = struct.pack('<BBBBHHII', width, height, 0, 0, 1, 32, len(png), offset)
        entries.append(entry)
        blobs.append(png)
        offset += len(png)
    return header + b''.join(entries) + b''.join(blobs)


def main():
    png_images = []
    for size in SIZES:
        img = draw_icon(size)
        png = encode_png(img)
        (ASSET_DIR / f'AuthorizedMangaDownloaderDesktop-{size}.png').write_bytes(png)
        png_images.append((size, png))
    ico = encode_ico(png_images)
    (ASSET_DIR / 'AuthorizedMangaDownloaderDesktop.ico').write_bytes(ico)
    print(ASSET_DIR / 'AuthorizedMangaDownloaderDesktop.ico')


if __name__ == '__main__':
    main()
