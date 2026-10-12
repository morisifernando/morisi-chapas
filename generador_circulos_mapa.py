#!/usr/bin/env python3
"""
Generador estilo mapa perforado pero con CÍRCULOS.
- Agujeros redondos pequeños
- Solo se colocan en zonas oscuras
- Fondos claros quedan casi vacíos
"""

import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


# ===================== PARÁMETROS =====================
HOLE_DIAM = 6.0          # mm (diámetro del círculo)
SEP = 9.0                # mm entre centros
SHEET_W = 2000.0
SHEET_H = 1000.0
FLANGE = 30.0
USABLE_W = SHEET_W - 2 * FLANGE
USABLE_H = SHEET_H - 2 * FLANGE

THRESHOLD = 0.55         # solo zonas más oscuras que esto


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

    px_per_mm = 5.0
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
    patch = img[y1:y2, x1:x2]
    return float(np.mean(patch)) / 255.0


def generate_holes(img: np.ndarray, design_w: float, design_h: float, px_per_mm: float):
    holes = []  # (x, y, diameter)

    margin = HOLE_DIAM / 2.0 + 1.0
    x = margin
    while x <= design_w - margin:
        y = margin
        while y <= design_h - margin:
            brightness = get_local_brightness(img, x, y, px_per_mm)

            if brightness < THRESHOLD:
                darkness = 1.0 - brightness
                strength = min(1.0, darkness / (1.0 - THRESHOLD + 0.01))
                if random.random() < (0.35 + 0.65 * strength):
                    holes.append((x, y, HOLE_DIAM))

            y += SEP
        x += SEP

    return holes


def export_preview(holes, design_w: float, design_h: float, output_path: str, scale: float = 4.0):
    prev_w = int(design_w * scale)
    prev_h = int(design_h * scale)

    preview = Image.new("RGB", (prev_w, prev_h), color=(235, 235, 232))
    draw = ImageDraw.Draw(preview)

    for x, y, diam in holes:
        r = (diam / 2.0) * scale
        cx = x * scale
        cy = y * scale
        bbox = [cx - r, cy - r, cx + r, cy + r]
        draw.ellipse(bbox, fill=(35, 35, 35))

    preview.save(output_path, quality=95)
    print(f"Preview guardado: {output_path}")
    return preview


def export_dxf(holes, design_w: float, design_h: float, output_path: str):
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

    # Contorno chapa
    add_line(0, 0, SHEET_W, 0)
    add_line(SHEET_W, 0, SHEET_W, SHEET_H)
    add_line(SHEET_W, SHEET_H, 0, SHEET_H)
    add_line(0, SHEET_H, 0, 0)

    # Área útil
    add_line(FLANGE, FLANGE, FLANGE + USABLE_W, FLANGE, "AREA_UTIL")
    add_line(FLANGE + USABLE_W, FLANGE, FLANGE + USABLE_W, FLANGE + USABLE_H, "AREA_UTIL")
    add_line(FLANGE + USABLE_W, FLANGE + USABLE_H, FLANGE, FLANGE + USABLE_H, "AREA_UTIL")
    add_line(FLANGE, FLANGE + USABLE_H, FLANGE, FLANGE, "AREA_UTIL")

    # Círculos
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

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"DXF guardado: {output_path}")


def main(imagen: str, ancho: float = 500.0, alto: float = 700.0, salida: str = "salida"):
    print("=== Generador CIRCULAR estilo mapa ===")
    print(f"Imagen: {imagen}")
    print(f"Área: {ancho} x {alto} mm")
    print(f"Diámetro agujero: {HOLE_DIAM} mm | Separación: {SEP} mm")
    print()

    img, design_w, design_h, px_per_mm = load_and_prepare_image(imagen, ancho, alto)
    print(f"Diseño real: {design_w:.1f} x {design_h:.1f} mm")

    holes = generate_holes(img, design_w, design_h, px_per_mm)
    print(f"Círculos generados: {len(holes)}")

    dxf_path = f"{salida}.dxf"
    preview_path = f"{salida}_preview.png"

    export_dxf(holes, design_w, design_h, dxf_path)
    export_preview(holes, design_w, design_h, preview_path)

    print("\n¡Listo!")
    return preview_path, dxf_path


if __name__ == "__main__":
    import sys
    img_path = sys.argv[1] if len(sys.argv) > 1 else "flor.png"
    main(img_path)
