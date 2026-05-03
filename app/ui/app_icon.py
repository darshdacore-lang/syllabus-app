from pathlib import Path
import struct
import zlib


BG = (33, 81, 69)
BORDER = (20, 51, 44)
PAPER = (247, 242, 231)
PAPER_SHADOW = (225, 214, 194)
INK = (42, 36, 29)
TOMATO = (216, 87, 71)
TOMATO_HIGHLIGHT = (244, 183, 171)
LEAF = (126, 167, 103)
LEAF_DARK = (79, 118, 69)
GOLD = (232, 197, 109)


def _inside_round_rect(x, y, left, top, right, bottom, radius):
    if left + radius <= x < right - radius or top + radius <= y < bottom - radius:
        return True

    corners = (
        (left + radius, top + radius),
        (right - radius - 1, top + radius),
        (left + radius, bottom - radius - 1),
        (right - radius - 1, bottom - radius - 1),
    )
    for cx, cy in corners:
        dx = x - cx
        dy = y - cy
        if dx * dx + dy * dy <= radius * radius:
            return True
    return False


def _inside_circle(x, y, cx, cy, radius):
    dx = x - cx
    dy = y - cy
    return dx * dx + dy * dy <= radius * radius


def _hex(color):
    return "#%02x%02x%02x" % color


def render_icon_pixels(size=1024):
    size = max(64, int(size))
    pixels = [[BG for _ in range(size)] for _ in range(size)]

    outer_pad = int(size * 0.05)
    outer_radius = int(size * 0.22)
    for y in range(size):
        for x in range(size):
            if not _inside_round_rect(x, y, outer_pad, outer_pad, size - outer_pad, size - outer_pad, outer_radius):
                pixels[y][x] = BORDER

    card_left = int(size * 0.16)
    card_top = int(size * 0.18)
    card_right = int(size * 0.62)
    card_bottom = int(size * 0.82)
    card_radius = int(size * 0.08)
    for y in range(card_top, card_bottom):
        for x in range(card_left, card_right):
            if _inside_round_rect(x, y, card_left, card_top, card_right, card_bottom, card_radius):
                shadow_band = x > card_right - int(size * 0.03)
                pixels[y][x] = PAPER_SHADOW if shadow_band else PAPER

    ring_x = card_left + int(size * 0.06)
    for y in range(card_top + int(size * 0.05), card_bottom - int(size * 0.05)):
        for width in range(int(size * 0.008)):
            pixels[y][ring_x + width] = GOLD

    line_specs = (
        (0.30, 0.12),
        (0.40, 0.23),
        (0.51, 0.19),
        (0.62, 0.25),
    )
    for y_ratio, width_ratio in line_specs:
        y = int(size * y_ratio)
        start = card_left + int(size * 0.12)
        end = start + int(size * width_ratio)
        thickness = max(2, int(size * 0.01))
        for yy in range(y, y + thickness):
            for xx in range(start, end):
                pixels[yy][xx] = INK

    tomato_cx = int(size * 0.72)
    tomato_cy = int(size * 0.36)
    tomato_radius = int(size * 0.17)
    highlight_cx = tomato_cx - int(size * 0.05)
    highlight_cy = tomato_cy - int(size * 0.05)
    for y in range(tomato_cy - tomato_radius, tomato_cy + tomato_radius):
        if not 0 <= y < size:
            continue
        for x in range(tomato_cx - tomato_radius, tomato_cx + tomato_radius):
            if not 0 <= x < size:
                continue
            if _inside_circle(x, y, tomato_cx, tomato_cy, tomato_radius):
                pixels[y][x] = TOMATO
                if _inside_circle(x, y, highlight_cx, highlight_cy, int(size * 0.05)):
                    pixels[y][x] = TOMATO_HIGHLIGHT

    leaf_top = tomato_cy - int(size * 0.20)
    leaf_bottom = tomato_cy - int(size * 0.10)
    leaf_left = tomato_cx - int(size * 0.05)
    leaf_right = tomato_cx + int(size * 0.08)
    for y in range(leaf_top, leaf_bottom):
        if not 0 <= y < size:
            continue
        for x in range(leaf_left, leaf_right):
            if not 0 <= x < size:
                continue
            center_pull = abs(x - tomato_cx) * 1.4
            taper = (y - leaf_top) * 0.9
            if center_pull + taper <= int(size * 0.08):
                pixels[y][x] = LEAF_DARK if x < tomato_cx else LEAF

    stem_x = tomato_cx + int(size * 0.005)
    stem_top = tomato_cy - int(size * 0.13)
    stem_bottom = tomato_cy - int(size * 0.03)
    for y in range(stem_top, stem_bottom):
        for x in range(stem_x, stem_x + max(2, int(size * 0.01))):
            if 0 <= x < size and 0 <= y < size:
                pixels[y][x] = LEAF_DARK

    clock_radius = int(size * 0.055)
    clock_cx = tomato_cx
    clock_cy = tomato_cy + int(size * 0.02)
    for y in range(clock_cy - clock_radius, clock_cy + clock_radius):
        if not 0 <= y < size:
            continue
        for x in range(clock_cx - clock_radius, clock_cx + clock_radius):
            if not 0 <= x < size:
                continue
            if _inside_circle(x, y, clock_cx, clock_cy, clock_radius):
                pixels[y][x] = PAPER
            if _inside_circle(x, y, clock_cx, clock_cy, clock_radius - max(2, int(size * 0.008))):
                pixels[y][x] = TOMATO

    hand_thickness = max(2, int(size * 0.008))
    for offset in range(hand_thickness):
        for x in range(clock_cx, clock_cx + int(size * 0.03)):
            pixels[clock_cy + offset][x] = PAPER
        for y in range(clock_cy - int(size * 0.03), clock_cy + 1):
            pixels[y][clock_cx + offset] = PAPER

    return pixels


def render_icon_rgba(size=1024):
    size = max(64, int(size))
    outer_pad = int(size * 0.05)
    outer_radius = int(size * 0.22)
    pixels = render_icon_pixels(size)
    rgba_rows = []
    for y, row in enumerate(pixels):
        rgba_row = []
        for x, color in enumerate(row):
            alpha = 255 if _inside_round_rect(
                x,
                y,
                outer_pad,
                outer_pad,
                size - outer_pad,
                size - outer_pad,
                outer_radius,
            ) else 0
            rgba_row.append((*color, alpha))
        rgba_rows.append(rgba_row)
    return rgba_rows


def build_photo_image(size=128):
    import tkinter as tk

    pixels = render_icon_pixels(size)
    image = tk.PhotoImage(width=size, height=size)
    for y, row in enumerate(pixels):
        image.put("{" + " ".join(_hex(color) for color in row) + "}", to=(0, y))
    return image


def write_ppm(path, size=1024):
    path = Path(path)
    pixels = render_icon_pixels(size)
    with path.open("wb") as file:
        file.write(f"P6\n{size} {size}\n255\n".encode("ascii"))
        for row in pixels:
            for red, green, blue in row:
                file.write(bytes((red, green, blue)))


def _png_chunk(chunk_type, data):
    return (
        struct.pack(">I", len(data))
        + chunk_type
        + data
        + struct.pack(">I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF)
    )


def write_png(path, size=1024):
    path = Path(path)
    pixels = render_icon_rgba(size)
    raw = bytearray()
    for row in pixels:
        raw.append(0)
        for red, green, blue, alpha in row:
            raw.extend((red, green, blue, alpha))

    width = len(pixels[0])
    height = len(pixels)
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)

    with path.open("wb") as file:
        file.write(b"\x89PNG\r\n\x1a\n")
        file.write(_png_chunk(b"IHDR", ihdr))
        file.write(_png_chunk(b"IDAT", zlib.compress(bytes(raw), 9)))
        file.write(_png_chunk(b"IEND", b""))
