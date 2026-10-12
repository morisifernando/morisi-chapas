#!/usr/bin/env python3
"""
Generador estilo mapa perforado (como la referencia).
- Agujeros cuadrados pequeños
- Solo se colocan en zonas oscuras de la imagen
- Fondos claros quedan casi vacíos
- La figura se reconoce bien de lejos
"""

import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


# ===================== PARÁMETROS =====================
HOLE_SIZE = 6.0          # mm (lado del cuadrado)
SEP = 9.0                # mm entre centros (deja ~3 mm de material entre agujeros)
SHEET_W = 2000.0
SHEET_H = 1000.0
FLANGE = 30.0
USABLE_W = SHEET_W - 2 * FLANGE
USABLE_H = SHEET_H - 2 * FLANGE

# Umbral: solo se colocan agujeros donde el brillo es menor a esto
# 0.0 = negro, 1.0 = blanco
THRESHOLD = 0.55         # más bajo = solo zonas más oscuras


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
        return 1.0  # fuera = claro

    r = 3
    x1, x2 = max(0, px - r), min(w, px + r + 1)
    y1, y2 = max(0, py - r), min(h, py + r + 1)
    patch = img[y1:y2, x1:x2]
    return float(np.mean(patch)) / 255.0


def generate_holes(img: np.ndarray, design_w: float, design_h: float, px_per_mm: float):
    """Genera agujeros cuadrados solo en zonas oscuras."""
    holes = []  # (x, y, size)

    margin = HOLE_SIZE / 2.0 + 1.0
    x = margin
    while x <= design_w - margin:
        y = margin
        while y <= design_h - margin:
            brightness = get_local_brightness(img, x, y, px_per_mm)

            if brightness < THRESHOLD:
                # Cuanto más oscuro, más probabilidad de colocar el agujero
                # (para dar un poco de variación natural)
                darkness = 1.0 - brightness
                # Normalizar respecto al umbral
                strength = min(1.0, darkness / (1.0 - THRESHOLD + 0.01))
                # Dejar pasar la mayoría de los oscuros, pocos de los medios
                if random.random() < (0.35 + 0.65 * strength):
                    holes.append((x, y, HOLE_SIZE))

            y += SEP
        x += SEP

    return holes


def export_preview(holes, design_w: float, design_h: float, output_path: str, scale: float = 4.0):
    prev_w = int(design_w * scale)
    prev_h = int(design_h * scale)

    # Fondo blanco/metal claro como la referencia
    preview = Image.new("RGB", (prev_w, prev_h), color=(235, 235, 232))
    draw = ImageDraw.Draw(preview)

    for x, y, size in holes:
        s = size * scale
        cx = x * scale
        cy = y * scale
        half = s / 2.0
        bbox = [cx - half, cy - half, cx + half, cy + half]
        draw.rectangle(bbox, fill=(40, 40, 40))

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

    # Agujeros cuadrados (4 líneas cada uno)
    for x, y, size in holes:
        cx = FLANGE + x
        cy = FLANGE + y
        half = size / 2.0
        x1, y1 = cx - half, cy - half
        x2, y2 = cx + half, cy + half
        add_line(x1, y1, x2, y1, "PERFORACIONES")
        add_line(x2, y1, x2, y2, "PERFORACIONES")
        add_line(x2, y2, x1, y2, "PERFORACIONES")
        add_line(x1, y2, x1, y1, "PERFORACIONES")

    lines.extend(["0", "ENDSEC", "0", "EOF"])

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"DXF guardado: {output_path}")


def main(imagen: str, ancho: float = 500.0, alto: float = 500.0, salida: str = "salida"):
    print("=== Generador estilo MAPA PERFORADO ===")
    print(f"Imagen: {imagen}")
    print(f"Área: {ancho} x {alto} mm")
    print(f"Agujero: {HOLE_SIZE} mm | Separación centros: {SEP} mm")
    print(f"Umbral de oscuridad: {THRESHOLD}")
    print()

    img, design_w, design_h, px_per_mm = load_and_prepare_image(imagen, ancho, alto)
    print(f"Diseño real: {design_w:.1f} x {design_h:.1f} mm")

    holes = generate_holes(img, design_w, design_h, px_per_mm)
    print(f"Agujeros generados: {len(holes)}")

    dxf_path = f"{salida}.dxf"
    preview_path = f"{salida}_preview.png"

    export_dxf(holes, design_w, design_h, dxf_path)
    export_preview(holes, design_w, design_h, preview_path)

    print("\n¡Listo!")
    return preview_path, dxf_path


if __name__ == "__main__":
    import sys
    img_path = sys.argv[1] if len(sys.argv) > 1 else "carlitos.jpg"
    main(img_path, ancho=550, alto=550, salida="estilo_mapa")
