#!/usr/bin/env python3
"""
Generador con ADAPTACIÓN AUTOMÁTICA según la imagen.
Analiza brillo, contraste y distribución para elegir
mejores parámetros de umbral, densidad y tamaños.
"""

import math
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageOps, ImageFilter, ImageEnhance


SHEET_W = 2000.0
SHEET_H = 1000.0
FLANGE = 30.0
USABLE_W = SHEET_W - 2 * FLANGE
USABLE_H = SHEET_H - 2 * FLANGE

MAX_FAILED = 18000
MAX_HOLES = 5000


def analyze_image(img: np.ndarray):
    """Analiza la imagen y devuelve parámetros adaptados."""
    pixels = img.flatten().astype(float) / 255.0

    mean_b = float(np.mean(pixels))
    std_b = float(np.std(pixels))
    p10 = float(np.percentile(pixels, 10))
    p50 = float(np.percentile(pixels, 50))
    p90 = float(np.percentile(pixels, 90))

    # Contraste aproximado
    contrast = p90 - p10

    print(f"  Análisis → brillo medio: {mean_b:.2f} | contraste: {contrast:.2f} | std: {std_b:.2f}")

    # --- Umbral adaptativo ---
    # Queremos capturar la parte significativa de la figura
    if mean_b > 0.75:          # imagen muy clara (fondo blanco)
        threshold = min(0.92, p50 + 0.25)
    elif mean_b < 0.35:        # imagen oscura
        threshold = max(0.40, p50 + 0.15)
    else:
        threshold = min(0.85, max(0.45, p50 + 0.18))

    # --- Rango de diámetros según contraste ---
    if contrast > 0.55:        # alto contraste → más variación
        diam_min, diam_max = 3.0, 11.0
    elif contrast < 0.30:      # bajo contraste → tamaños más parecidos
        diam_min, diam_max = 4.0, 8.0
    else:
        diam_min, diam_max = 3.0, 10.0

    # --- Separación mínima ---
    sep_min = 2.5 if contrast > 0.45 else 3.5

    print(f"  Parámetros auto → umbral: {threshold:.2f} | diámetros: {diam_min}-{diam_max} mm | sep: {sep_min} mm")

    return {
        "threshold": threshold,
        "diam_min": diam_min,
        "diam_max": diam_max,
        "sep_min": sep_min,
        "mean_b": mean_b,
        "contrast": contrast,
    }


def enhance_for_perforation(pil_img: Image.Image) -> Image.Image:
    """Mejora contraste y nitidez para que la figura se separe mejor del fondo."""
    # Convertir a grises
    img = pil_img.convert("L")

    # Autocontraste suave
    img = ImageOps.autocontrast(img, cutoff=1)

    # Un poco más de contraste
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.35)

    # Ligero sharpen
    img = img.filter(ImageFilter.UnsharpMask(radius=1.2, percent=120, threshold=2))

    return img


def load_and_prepare(path: str, target_w: float, target_h: float):
    pil = Image.open(path)
    pil = enhance_for_perforation(pil)

    w, h = pil.size
    aspect = w / h

    if target_w / target_h > aspect:
        design_h = target_h
        design_w = design_h * aspect
    else:
        design_w = target_w
        design_h = design_w / aspect

    px_per_mm = 4.5
    img_w = max(50, int(design_w * px_per_mm))
    img_h = max(50, int(design_h * px_per_mm))
    img_resized = pil.resize((img_w, img_h), Image.Resampling.LANCZOS)

    return np.array(img_resized), design_w, design_h, px_per_mm


def get_brightness(img: np.ndarray, x_mm: float, y_mm: float, px_per_mm: float) -> float:
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
    return math.hypot(c1[0] - c2[0], c1[1] - c2[1]) < (c1[2] + c2[2] + sep)


def generate_auto(img, design_w, design_h, px_per_mm, params, seed=42):
    random.seed(seed)
    threshold = params["threshold"]
    diam_min = params["diam_min"]
    diam_max = params["diam_max"]
    sep_min = params["sep_min"]

    holes = []
    failed = 0

    while failed < MAX_FAILED and len(holes) < MAX_HOLES:
        # Muestreo un poco sesgado hacia el centro (suele haber más figura)
        if random.random() < 0.7:
            x = random.gauss(design_w / 2, design_w / 3.2)
            y = random.gauss(design_h / 2, design_h / 3.2)
            x = max(0, min(design_w, x))
            y = max(0, min(design_h, y))
        else:
            x = random.uniform(0, design_w)
            y = random.uniform(0, design_h)

        brightness = get_brightness(img, x, y, px_per_mm)
        if brightness >= threshold:
            failed += 1
            continue

        # Mapear brillo → diámetro
        t = max(0.0, min(1.0, brightness / threshold))
        diam = diam_max - t * (diam_max - diam_min)
        diam *= random.uniform(0.88, 1.12)
        diam = max(diam_min, min(diam_max, diam))
        radius = diam / 2.0

        if (x - radius < 0 or x + radius > design_w or
                y - radius < 0 or y + radius > design_h):
            failed += 1
            continue

        candidate = (x, y, radius)
        if any(overlaps(candidate, h, sep_min) for h in holes):
            failed += 1
            continue

        holes.append(candidate)
        failed = 0

    return [(x, y, r * 2) for x, y, r in holes]


def export_preview(holes, design_w, design_h, output_path, scale=3.5):
    prev_w = int(design_w * scale)
    prev_h = int(design_h * scale)
    preview = Image.new("RGB", (prev_w, prev_h), color=(230, 230, 228))
    draw = ImageDraw.Draw(preview)

    for x, y, diam in holes:
        r = (diam / 2.0) * scale
        cx, cy = x * scale, y * scale
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(25, 25, 28))

    preview.save(output_path, quality=95)
    print(f"Preview: {output_path}")


def export_dxf(holes, output_path):
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


def main(imagen: str, ancho: float = 480.0, alto: float = 560.0, salida: str = "auto", seed: int = 42):
    print("=== Generador con ADAPTACIÓN AUTOMÁTICA ===")
    print(f"Imagen: {imagen}")
    print()

    img, design_w, design_h, px_per_mm = load_and_prepare(imagen, ancho, alto)
    print(f"Diseño: {design_w:.0f} x {design_h:.0f} mm")

    params = analyze_image(img)

    holes = generate_auto(img, design_w, design_h, px_per_mm, params, seed=seed)
    print(f"Círculos generados: {len(holes)}")
    if holes:
        diams = [d for _, _, d in holes]
        print(f"Promedio: {np.mean(diams):.1f} mm | Rango: {min(diams):.1f}-{max(diams):.1f} mm")

    export_dxf(holes, f"{salida}.dxf")
    export_preview(holes, design_w, design_h, f"{salida}_preview.png")
    print("\n¡Listo!")


if __name__ == "__main__":
    import sys
    img = sys.argv[1] if len(sys.argv) > 1 else "perro.png"
    main(img, salida="perro_auto")
