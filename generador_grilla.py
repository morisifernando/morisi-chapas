#!/usr/bin/env python3
"""
Generador de perforaciones en CUADRÍCULA REGULAR
Para que la imagen se reconozca cuando te alejás (efecto halftone).
"""

import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


# ===================== PARÁMETROS =====================
DIAM_MIN = 5.0           # mm
DIAM_MAX = 20.0          # mm
SEP_BORDE = 5.0          # mm de separación borde a borde
SEP_CENTROS = DIAM_MAX + SEP_BORDE  # 25 mm entre centros
SHEET_W = 2000.0
SHEET_H = 1000.0
FLANGE = 30.0
USABLE_W = SHEET_W - 2 * FLANGE
USABLE_H = SHEET_H - 2 * FLANGE


def brightness_to_diameter(brightness: float) -> float:
    """0.0 (negro) → DIAM_MAX, 1.0 (blanco) → DIAM_MIN"""
    t = 1.0 - brightness
    return DIAM_MIN + t * (DIAM_MAX - DIAM_MIN)


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

    # Resolución alta para buen muestreo
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
        return 0.5

    r = 5
    x1, x2 = max(0, px - r), min(w, px + r + 1)
    y1, y2 = max(0, py - r), min(h, py + r + 1)
    patch = img[y1:y2, x1:x2]
    return float(np.mean(patch)) / 255.0


def generate_grid_circles(img: np.ndarray, design_w: float, design_h: float, px_per_mm: float):
    """Genera círculos en cuadrícula regular.
    En fondos plenos claros se eliminan la mayoría de los agujeros
    para que la imagen se note más.
    """
    import random
    circles = []

    # Empezar con margen para que el círculo más grande no se salga
    margin = DIAM_MAX / 2.0 + 1.0
    x = margin
    while x <= design_w - margin:
        y = margin
        while y <= design_h - margin:
            brightness = get_local_brightness(img, x, y, px_per_mm)
            diam = brightness_to_diameter(brightness)

            # --- Lógica de eliminación en fondos plenos ---
            # brightness cerca de 1.0 = muy claro (fondo)
            # Cuanto más claro, más probabilidad de NO colocar el círculo
            if brightness > 0.75:
                # Fondo claro: solo dejar pasar un pequeño porcentaje
                # 0.75 → 40% de chance de quedar
                # 0.90 → 15% de chance
                # 0.98 → casi 0%
                keep_chance = max(0.0, 1.0 - (brightness - 0.70) * 3.5)
                if random.random() > keep_chance:
                    y += SEP_CENTROS
                    continue

            # Solo agregar si tiene un tamaño mínimo razonable
            if diam >= DIAM_MIN * 0.9:
                circles.append((x, y, diam))

            y += SEP_CENTROS
        x += SEP_CENTROS

    return circles


def export_preview(circles, design_w: float, design_h: float, output_path: str, scale: float = 3.0):
    prev_w = int(design_w * scale)
    prev_h = int(design_h * scale)

    preview = Image.new("RGB", (prev_w, prev_h), color=(175, 178, 182))
    draw = ImageDraw.Draw(preview)

    for x, y, diam in circles:
        r = (diam / 2.0) * scale
        cx = x * scale
        cy = y * scale
        bbox = [cx - r, cy - r, cx + r, cy + r]
        draw.ellipse(bbox, fill=(22, 22, 25), outline=(12, 12, 15))

    preview.save(output_path, quality=95)
    print(f"Preview guardado: {output_path}")
    return preview


def export_simple_dxf(circles, design_w: float, design_h: float, output_path: str):
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
    for x, y, diam in circles:
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


def main(imagen: str, ancho: float = 400.0, alto: float = 400.0, salida: str = "salida"):
    print("=== Generador en CUADRÍCULA (efecto de lejos se ve la imagen) ===")
    print(f"Imagen: {imagen}")
    print(f"Área objetivo: {ancho} x {alto} mm")
    print(f"Separación entre centros: {SEP_CENTROS} mm")
    print(f"Diámetros: {DIAM_MIN} – {DIAM_MAX} mm")
    print()

    img, design_w, design_h, px_per_mm = load_and_prepare_image(imagen, ancho, alto)
    print(f"Diseño real: {design_w:.1f} x {design_h:.1f} mm")

    circles = generate_grid_circles(img, design_w, design_h, px_per_mm)
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
    main(img_path, ancho=450, alto=450, salida="candado_grilla")
