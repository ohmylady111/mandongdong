#!/usr/bin/env python3
from __future__ import annotations

import math
import shutil
import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ASSET_DIR = ROOT / "windows-exe-bundle" / "assets"
ASSET_DIR.mkdir(parents=True, exist_ok=True)

BG_TOP = (88, 62, 186, 255)
BG_BOTTOM = (23, 26, 72, 255)
ACCENT = (244, 114, 182, 255)      # pink
ACCENT2 = (96, 165, 250, 255)      # blue
ACCENT3 = (34, 211, 238, 255)      # cyan
WHITE = (249, 250, 255, 255)
PAPER = (240, 238, 252, 255)
INK = (67, 56, 111, 255)
DOT = (194, 180, 240, 180)
SHADOW = (5, 5, 18, 95)
GLOW_PINK = (244, 114, 182, 44)
GLOW_CYAN = (34, 211, 238, 40)
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
    corners = [(x + r, y + r), (x + w - r, y + r), (x + r, y + h - r), (x + w - r, y + h - r)]
    return any((px - cx) ** 2 + (py - cy) ** 2 <= r ** 2 for cx, cy in corners)


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
        for _ in range(n):
            row.append(base)
        img.append(row)
    return img


def draw_star(img, cx, cy, r1, r2, points, color):
    pts = []
    for i in range(points * 2):
        ang = -math.pi / 2 + i * math.pi / points
        r = r1 if i % 2 == 0 else r2
        pts.append((cx + math.cos(ang) * r, cy + math.sin(ang) * r))
    draw_polygon(img, pts, color)


def draw_dots(img, x, y, w, h, spacing, radius, color):
    yy = y
    row = 0
    while yy < y + h:
        xx = x + (spacing / 2 if row % 2 else 0)
        while xx < x + w:
            draw_circle(img, xx, yy, radius, color)
            xx += spacing
        yy += spacing
        row += 1


def draw_icon(n):
    img = make_canvas(n)

    # glows / manga energy
    draw_circle(img, n * 0.22, n * 0.2, n * 0.22, GLOW_PINK)
    draw_circle(img, n * 0.82, n * 0.32, n * 0.24, GLOW_CYAN)
    draw_circle(img, n * 0.55, n * 0.86, n * 0.25, (ACCENT2[0], ACCENT2[1], ACCENT2[2], 30))

    # background speed lines
    for frac in [0.18, 0.28, 0.38, 0.48]:
        draw_line(img, n * 0.04, n * frac, n * 0.34, n * (frac - 0.1), max(1.0, n * 0.012), (255, 255, 255, 20))
    for frac in [0.42, 0.53, 0.64]:
        draw_line(img, n * 0.72, n * frac, n * 0.97, n * (frac - 0.12), max(1.0, n * 0.012), (255, 255, 255, 18))

    # sparkles
    draw_star(img, n * 0.77, n * 0.18, n * 0.045, n * 0.018, 4, (255, 255, 255, 180))
    draw_star(img, n * 0.19, n * 0.74, n * 0.03, n * 0.012, 4, (255, 255, 255, 145))

    # manga pages
    px = n * 0.18
    py = n * 0.18
    page_w = n * 0.48
    page_h = n * 0.56
    rr = n * 0.055

    draw_round_rect(img, px + n * 0.055, py + n * 0.02, page_w, page_h, rr, SHADOW)
    draw_round_rect(img, px, py + n * 0.05, page_w, page_h, rr, PAPER)
    draw_round_rect(img, px + n * 0.04, py, page_w, page_h, rr, WHITE)

    # page fold
    fold = [(px + page_w - n * 0.095, py), (px + page_w + n * 0.04, py), (px + page_w + n * 0.04, py + n * 0.1)]
    draw_polygon(img, fold, (229, 221, 249, 255))

    # manga panel frames on front page
    fx = px + n * 0.07
    fy = py + n * 0.07
    fw = page_w - n * 0.12
    fh = page_h - n * 0.12
    draw_round_rect(img, fx, fy, fw * 0.44, fh * 0.42, n * 0.015, (245, 243, 255, 255))
    draw_round_rect(img, fx + fw * 0.5, fy, fw * 0.5, fh * 0.25, n * 0.015, (246, 239, 255, 255))
    draw_round_rect(img, fx + fw * 0.5, fy + fh * 0.31, fw * 0.5, fh * 0.53, n * 0.015, (247, 242, 255, 255))
    draw_round_rect(img, fx, fy + fh * 0.48, fw * 0.44, fh * 0.36, n * 0.015, (244, 242, 255, 255))

    # screentone dots inside one panel
    draw_dots(img, fx + n * 0.03, fy + n * 0.03, fw * 0.36, fh * 0.34, max(2, n * 0.045), max(0.8, n * 0.008), DOT)
    # panel lines
    draw_line(img, fx + fw * 0.5, fy + fh * 0.08, fx + fw * 0.92, fy + fh * 0.18, max(1.0, n * 0.01), (198, 187, 235, 255))
    draw_line(img, fx + fw * 0.55, fy + fh * 0.46, fx + fw * 0.9, fy + fh * 0.38, max(1.0, n * 0.01), (194, 176, 235, 255))
    draw_line(img, fx + fw * 0.1, fy + fh * 0.62, fx + fw * 0.35, fy + fh * 0.74, max(1.0, n * 0.01), (202, 184, 239, 255))

    # speech bubble accent
    bubble = [
        (px + n * 0.16, py + n * 0.54),
        (px + n * 0.31, py + n * 0.54),
        (px + n * 0.33, py + n * 0.63),
        (px + n * 0.24, py + n * 0.63),
        (px + n * 0.2, py + n * 0.68),
        (px + n * 0.2, py + n * 0.63),
        (px + n * 0.14, py + n * 0.63),
    ]
    draw_polygon(img, bubble, (255, 255, 255, 210))

    # download arrow (pink with cyan highlight)
    shaft_x = n * 0.73
    shaft_top = n * 0.3
    shaft_bottom = n * 0.62
    thick = n * 0.1
    draw_line(img, shaft_x + n * 0.014, shaft_top + n * 0.02, shaft_x + n * 0.014, shaft_bottom + n * 0.02, thick, SHADOW)
    draw_polygon(img, [
        (shaft_x - n * 0.12 + n * 0.014, n * 0.57 + n * 0.02),
        (shaft_x + n * 0.12 + n * 0.014, n * 0.57 + n * 0.02),
        (shaft_x + n * 0.014, n * 0.79 + n * 0.02),
    ], SHADOW)

    draw_line(img, shaft_x, shaft_top, shaft_x, shaft_bottom, thick, ACCENT)
    draw_polygon(img, [
        (shaft_x - n * 0.12, n * 0.57),
        (shaft_x + n * 0.12, n * 0.57),
        (shaft_x, n * 0.79),
    ], ACCENT)
    draw_line(img, shaft_x - n * 0.02, shaft_top + n * 0.02, shaft_x - n * 0.02, shaft_bottom - n * 0.03, n * 0.022, ACCENT3)

    # tray / underline
    tray = [(n * 0.58, n * 0.8), (n * 0.86, n * 0.8), (n * 0.82, n * 0.89), (n * 0.62, n * 0.89)]
    draw_polygon(img, tray, (25, 22, 63, 225))
    draw_line(img, n * 0.62, n * 0.89, n * 0.82, n * 0.89, n * 0.03, ACCENT3)

    # top edge gloss
    draw_round_rect(img, n * 0.06, n * 0.06, n * 0.88, n * 0.88, n * 0.2, (255, 255, 255, 10))
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
        (ASSET_DIR / f'AuthorizedMangaDownloaderDesktop-anime-{size}.png').write_bytes(png)
        png_images.append((size, png))
    ico = encode_ico(png_images)
    anime_ico = ASSET_DIR / 'AuthorizedMangaDownloaderDesktop-anime.ico'
    anime_ico.write_bytes(ico)
    # user selected style 2 -> make it the default icon too
    shutil.copy2(anime_ico, ASSET_DIR / 'AuthorizedMangaDownloaderDesktop.ico')
    shutil.copy2(ASSET_DIR / 'AuthorizedMangaDownloaderDesktop-anime-256.png', ASSET_DIR / 'AuthorizedMangaDownloaderDesktop-256.png')
    print(anime_ico)


if __name__ == '__main__':
    main()
