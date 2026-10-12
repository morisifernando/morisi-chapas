#!/usr/bin/env python3
"""
Generador simplificado de perforaciones (solo Pillow + numpy)
- Sin opencv ni ezdxf (por problemas de red)
- Genera preview PNG de alta calidad
- También genera un DXF básico a mano (texto)
"""

import math
import random
import struct
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageOps


# ===================== PARÁMETROS =====================
DIAM_MIN = 10.0          # mm
DIAM_MAX = 30.0          # mm
SEP_MIN = 7.0            # mm borde a borde
SHEET_W = 2000.0
SHEET_H = 1000.0
FLANGE = 30.0
USABLE_W = SHEET_W - 2 * FLANGE
USABLE_H = SHEET_H - 2 * FLANGE

MAX_FAILED_ATTEMPTS = 12000
MAX_CIRCLES = 3000


def brightness_to_diameter(brightness: float) -> float:
    """0.0 (negro) → DIAM_MAX, 1.0 (blanco) → DIAM_MIN"""
    t = 1.0 - brightness
    return DIAM_MIN + t * (DIAM_MAX - DIAM_MIN)


def load_and_prepare_image(path: str, target_w: float, target_h: float):
    img = Image.open(path).convert("L")  # escala de grises
    w, h = img.size
    aspect = w / h

    if target_w / target_h > aspect:
        design_h = target_h
        design_w = design_h * aspect
    else:
        design_w = target_w
        design_h = design_w / aspect

    px_per_mm = 3.0
    img_w = max(50, int(design_w * px_per_mm))
    img_h = max(50, int(design_h * px_per_mm))
    img_resized = img.resize((img_w, img_h), Image.Resampling.LANCZOS)

    return np.array(img_resized), design_w, design_h, px_per_mm


def get_local_brightness(img: np.ndarray, x_mm: float, y_mm: float,
                         px_per_mm: float) -> float:
    px = int(x_mm * px_per_mm)
    py = int(y_mm * px_per_mm)
    h, w = img.shape
    if px < 0 or px >= w or py < 0 or py >= h:
        return 0.5

    r = 4
    x1, x2 = max(0, px - r), min(w, px + r + 1)
    y1, y2 = max(0, py - r), min(h, py + r + 1)
    patch = img[y1:y2, x1:x2]
    return float(np.mean(patch)) / 255.0


def circles_overlap(c1, c2, sep_min: float) -> bool:
    x1, y1, r1 = c1
    x2, y2, r2 = c2
    dist = math.hypot(x1 - x2, y1 - y2)
    return dist < (r1 + r2 + sep_min)


def generate_circles(img: np.ndarray, design_w: float, design_h: float,
                     px_per_mm: float, seed: int | None = None):
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)

    circles = []
    failed = 0

    while failed < MAX_FAILED_ATTEMPTS and len(circles) < MAX_CIRCLES:
        x = random.uniform(0, design_w)
        y = random.uniform(0, design_h)

        brightness = get_local_brightness(img, x, y, px_per_mm)
        diam = brightness_to_diameter(brightness)
        radius = diam / 2.0

        if (x - radius < 0 or x + radius > design_w or
                y - radius < 0 or y + radius > design_h):
            failed += 1
            continue

        candidate = (x, y, radius)
        collision = any(circles_overlap(candidate, ex, SEP_MIN) for ex in circles)

        if collision:
            failed += 1
            continue

        circles.append(candidate)
        failed = 0

    return [(x, y, r * 2) for x, y, r in circles]


def export_preview(circles, design_w: float, design_h: float, output_path: str,
                   scale: float = 3.0):
    prev_w = int(design_w * scale)
    prev_h = int(design_h * scale)

    # Fondo metalizado
    preview = Image.new("RGB", (prev_w, prev_h), color=(175, 178, 182))
    draw = ImageDraw.Draw(preview)

    for x, y, diam in circles:
        r = (diam / 2.0) * scale
        cx = x * scale
        cy = y * scale
        bbox = [cx - r, cy - r, cx + r, cy + r]
        draw.ellipse(bbox, fill=(25, 25, 28), outline=(15, 15, 18))

    preview.save(output_path, quality=95)
    print(f"Preview guardado: {output_path}")
    return preview


def export_simple_dxf(circles, design_w: float, design_h: float, output_path: str):
    """Genera un DXF mínimo a mano (sin librería)."""
    lines = [
        "0", "SECTION",
        "2", "HEADER",
        "0", "ENDSEC",
        "0", "SECTION",
        "2", "TABLES",
        "0", "ENDSEC",
        "0", "SECTION",
        "2", "BLOCKS",
        "0", "ENDSEC",
        "0", "SECTION",
        "2", "ENTITIES",
    ]

    # Contorno de la chapa
    def add_line(x1, y1, x2, y2):
        lines.extend([
            "0", "LINE",
            "8", "CONTORNO",
            "10", f"{x1:.3f}", "20", f"{y1:.3f}", "30", "0.0",
            "11", f"{x2:.3f}", "21", f"{y2:.3f}", "31", "0.0",
        ])

    # Rectángulo chapa
    add_line(0, 0, SHEET_W, 0)
    add_line(SHEET_W, 0, SHEET_W, SHEET_H)
    add_line(SHEET_W, SHEET_H, 0, SHEET_H)
    add_line(0, SHEET_H, 0, 0)

    # Área útil
    add_line(FLANGE, FLANGE, FLANGE + USABLE_W, FLANGE)
    add_line(FLANGE + USABLE_W, FLANGE, FLANGE + USABLE_W, FLANGE + USABLE_H)
    add_line(FLANGE + USABLE_W, FLANGE + USABLE_H, FLANGE, FLANGE + USABLE_H)
    add_line(FLANGE, FLANGE + USABLE_H, FLANGE, FLANGE)

    # Círculos
    for x, y, diam in circles:
        cx = FLANGE + x
        cy = FLANGE + y
        r = diam / 2.0
        lines.extend([
            "0", "CIRCLE",
            "8", "PERFORACIONES",
            "10", f"{cx:.3f}",
            "20", f"{cy:.3f}",
            "30", "0.0",
            "40", f"{r:.3f}",
        ])

    lines.extend(["0", "ENDSEC", "0", "EOF"])

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"DXF guardado: {output_path}")


def main(imagen: str, ancho: float = 400.0, alto: float = 400.0,
         seed: int = 42, salida: str = "salida"):
    print("=== Generador de perforaciones (versión simple) ===")
    print(f"Imagen: {imagen}")
    print(f"Área objetivo: {ancho} x {alto} mm")
    print()

    img, design_w, design_h, px_per_mm = load_and_prepare_image(imagen, ancho, alto)
    print(f"Diseño real: {design_w:.1f} x {design_h:.1f} mm")

    print("Generando círculos...")
    circles = generate_circles(img, design_w, design_h, px_per_mm, seed=seed)
    print(f"Círculos generados: {len(circles)}")

    if circles:
        diams = [d for _, _, d in circles]
        print(f"Diámetro promedio: {np.mean(diams):.1f} mm")
        print(f"Diámetro mín/máx: {min(diams):.1f} / {max(diams):.1f} mm")

    dxf_path = f"{salida}.dxf"
    preview_path = f"{salida}_preview.png"

    export_simple_dxf(circles, design_w, design_h, dxf_path)
    export_preview(circles, design_w, design_h, preview_path)

    print("\n¡Listo!")
    return preview_path, dxf_path


if __name__ == "__main__":
    import sys
    img_path = sys.argv[1] if len(sys.argv) > 1 else "candado.png"
    main(img_path, ancho=400, alto=400, seed=42, salida="candado_salida")
