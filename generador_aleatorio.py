#!/usr/bin/env python3
"""
Generador con disposición ALEATORIA + tamaño variable.
Soporta círculos (por ahora). Preparado para cuadrados/triángulos.
"""

import math
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


# ===================== PARÁMETROS =====================
DIAM_MIN = 3.0
DIAM_MAX = 10.0
SEP_MIN = 3.0            # separación mínima borde a borde
SHEET_W = 2000.0
SHEET_H = 1000.0
FLANGE = 30.0
USABLE_W = SHEET_W - 2 * FLANGE
USABLE_H = SHEET_H - 2 * FLANGE

MAX_FAILED = 15000
MAX_HOLES = 4000
THRESHOLD = 0.80         # más permisivo para imágenes claras


def brightness_to_diameter(brightness: float) -> float:
    t = max(0.0, min(1.0, brightness / THRESHOLD))
    return DIAM_MAX - t * (DIAM_MAX - DIAM_MIN)


def load_and_prepare_image(path: str, target_w: float, target_h: float):
    img = Image.open(path).convert("L")
    w, h = img.size
    aspect = w / h

    if target_w / target_h > aspect:
        design_h = target_h
        design_w = design_h * aspect
    else:
        design_w = target_w
        design_h = design_w / aspect

    px_per_mm = 4.0
    img_w = max(40, int(design_w * px_per_mm))
    img_h = max(40, int(design_h * px_per_mm))
    img_resized = img.resize((img_w, img_h), Image.Resampling.LANCZOS)
    return np.array(img_resized), design_w, design_h, px_per_mm


def get_local_brightness(img: np.ndarray, x_mm: float, y_mm: float, px_per_mm: float) -> float:
    px = int(x_mm * px_per_mm)
    py = int(y_mm * px_per_mm)
    h, w = img.shape
    if px < 0 or px >= w or py < 0 or py >= h:
        return 1.0
    r = 3
    x1, x2 = max(0, px - r), min(w, px + r + 1)
    y1, y2 = max(0, py - r), min(h, py + r + 1)
    return float(np.mean(img[y1:y2, x1:x2])) / 255.0


def overlaps(c1, c2, sep):
    x1, y1, r1 = c1
    x2, y2, r2 = c2
    return math.hypot(x1 - x2, y1 - y2) < (r1 + r2 + sep)


def generate_random(img, design_w, design_h, px_per_mm, seed=None):
    if seed is not None:
        random.seed(seed)

    holes = []  # (x, y, radius)
    failed = 0

    # Primero intentamos sesgar el muestreo hacia zonas más oscuras
    while failed < MAX_FAILED and len(holes) < MAX_HOLES:
        x = random.uniform(0, design_w)
        y = random.uniform(0, design_h)

        brightness = get_local_brightness(img, x, y, px_per_mm)
        if brightness >= THRESHOLD:
            failed += 1
            continue

        diam = brightness_to_diameter(brightness)
        diam *= random.uniform(0.9, 1.1)
        diam = max(DIAM_MIN, min(DIAM_MAX, diam))
        radius = diam / 2.0

        if (x - radius < 0 or x + radius > design_w or
                y - radius < 0 or y + radius > design_h):
            failed += 1
            continue

        candidate = (x, y, radius)
        if any(overlaps(candidate, h, SEP_MIN) for h in holes):
            failed += 1
            continue

        holes.append(candidate)
        failed = 0

    return [(x, y, r * 2) for x, y, r in holes]


def export_preview(holes, design_w, design_h, output_path, scale=3.5):
    prev_w = int(design_w * scale)
    prev_h = int(design_h * scale)
    preview = Image.new("RGB", (prev_w, prev_h), color=(232, 232, 230))
    draw = ImageDraw.Draw(preview)

    for x, y, diam in holes:
        r = (diam / 2.0) * scale
        cx, cy = x * scale, y * scale
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(28, 28, 30))

    preview.save(output_path, quality=95)
    print(f"Preview: {output_path}")


def export_dxf(holes, design_w, design_h, output_path):
    lines = [
        "0", "SECTION", "2", "HEADER", "0", "ENDSEC",
        "0", "SECTION", "2", "TABLES", "0", "ENDSEC",
        "0", "SECTION", "2", "BLOCKS", "0", "ENDSEC",
        "0", "SECTION", "2", "ENTITIES",
    ]

    def add_line(x1, y1, x2, y2, layer="CONTORNO"):
        lines.extend([
            "0", "LINE", "8", layer,
            "10", f"{x1:.3f}", "20", f"{y1:.3f}", "30", "0.0",
            "11", f"{x2:.3f}", "21", f"{y2:.3f}", "31", "0.0",
        ])

    add_line(0, 0, SHEET_W, 0)
    add_line(SHEET_W, 0, SHEET_W, SHEET_H)
    add_line(SHEET_W, SHEET_H, 0, SHEET_H)
    add_line(0, SHEET_H, 0, 0)

    for x, y, diam in holes:
        cx = FLANGE + x
        cy = FLANGE + y
        r = diam / 2.0
        lines.extend([
            "0", "CIRCLE", "8", "PERFORACIONES",
            "10", f"{cx:.3f}", "20", f"{cy:.3f}", "30", "0.0",
            "40", f"{r:.3f}",
        ])

    lines.extend(["0", "ENDSEC", "0", "EOF"])
    with open(output_path, "w") as f:
        f.write("\n".join(lines))
    print(f"DXF: {output_path}")


def main(imagen, ancho=450, alto=550, salida="aleatorio", seed=42):
    print("=== Generador ALEATORIO (tamaño variable) ===")
    print(f"Imagen: {imagen}")
    print(f"Diámetros: {DIAM_MIN}-{DIAM_MAX} mm | Sep. mín: {SEP_MIN} mm")
    print()

    img, design_w, design_h, px_per_mm = load_and_prepare_image(imagen, ancho, alto)
    print(f"Diseño: {design_w:.0f} x {design_h:.0f} mm")

    holes = generate_random(img, design_w, design_h, px_per_mm, seed=seed)
    print(f"Círculos: {len(holes)}")
    if holes:
        diams = [d for _, _, d in holes]
        print(f"Promedio: {np.mean(diams):.1f} mm | Rango: {min(diams):.1f}-{max(diams):.1f} mm")

    export_dxf(holes, design_w, design_h, f"{salida}.dxf")
    export_preview(holes, design_w, design_h, f"{salida}_preview.png")
    print("¡Listo!")


if __name__ == "__main__":
    main("perro.png", ancho=450, alto=550, salida="perro_aleatorio")
