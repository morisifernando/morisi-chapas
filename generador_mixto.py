#!/usr/bin/env python3
"""
Generador MIXTO: círculos + cuadrados + triángulos
con adaptación automática y disposición aleatoria.
"""

import math
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageOps, ImageFilter, ImageEnhance


SHEET_W = 2000.0
SHEET_H = 1000.0
FLANGE = 30.0

MAX_FAILED = 18000
MAX_HOLES = 4500
SHAPES = ["circle", "square", "triangle"]


def analyze_image(img: np.ndarray):
    pixels = img.flatten().astype(float) / 255.0
    mean_b = float(np.mean(pixels))
    p10 = float(np.percentile(pixels, 10))
    p50 = float(np.percentile(pixels, 50))
    p90 = float(np.percentile(pixels, 90))
    contrast = p90 - p10

    if mean_b > 0.75:
        threshold = min(0.92, p50 + 0.25)
    elif mean_b < 0.35:
        threshold = max(0.40, p50 + 0.15)
    else:
        threshold = min(0.85, max(0.45, p50 + 0.18))

    if contrast > 0.55:
        diam_min, diam_max = 3.5, 11.0
    elif contrast < 0.30:
        diam_min, diam_max = 4.0, 8.5
    else:
        diam_min, diam_max = 3.5, 10.0

    sep_min = 2.8 if contrast > 0.45 else 3.5

    print(f"  Auto → umbral:{threshold:.2f} | tamaños:{diam_min}-{diam_max} | sep:{sep_min}")
    return {
        "threshold": threshold,
        "diam_min": diam_min,
        "diam_max": diam_max,
        "sep_min": sep_min,
    }


def enhance(pil_img):
    img = pil_img.convert("L")
    img = ImageOps.autocontrast(img, cutoff=1)
    img = ImageEnhance.Contrast(img).enhance(1.35)
    img = img.filter(ImageFilter.UnsharpMask(radius=1.2, percent=120, threshold=2))
    return img


def load_and_prepare(path, target_w, target_h):
    pil = enhance(Image.open(path))
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
    arr = np.array(pil.resize((img_w, img_h), Image.Resampling.LANCZOS))
    return arr, design_w, design_h, px_per_mm


def get_brightness(img, x_mm, y_mm, px_per_mm):
    px, py = int(x_mm * px_per_mm), int(y_mm * px_per_mm)
    h, w = img.shape
    if px < 0 or px >= w or py < 0 or py >= h:
        return 1.0
    r = 3
    return float(np.mean(img[max(0, py-r):min(h, py+r+1), max(0, px-r):min(w, px+r+1)])) / 255.0


def overlaps(a, b, sep):
    # a, b = (x, y, radius_equiv)
    return math.hypot(a[0]-b[0], a[1]-b[1]) < (a[2] + b[2] + sep)


def generate_mixed(img, design_w, design_h, px_per_mm, params, seed=42):
    random.seed(seed)
    threshold = params["threshold"]
    dmin, dmax = params["diam_min"], params["diam_max"]
    sep = params["sep_min"]

    holes = []  # (x, y, size, shape)
    failed = 0

    while failed < MAX_FAILED and len(holes) < MAX_HOLES:
        if random.random() < 0.7:
            x = max(0, min(design_w, random.gauss(design_w/2, design_w/3.2)))
            y = max(0, min(design_h, random.gauss(design_h/2, design_h/3.2)))
        else:
            x = random.uniform(0, design_w)
            y = random.uniform(0, design_h)

        brightness = get_brightness(img, x, y, px_per_mm)
        if brightness >= threshold:
            failed += 1
            continue

        t = max(0.0, min(1.0, brightness / threshold))
        size = dmax - t * (dmax - dmin)
        size *= random.uniform(0.88, 1.12)
        size = max(dmin, min(dmax, size))
        radius = size / 2.0

        if (x - radius < 0 or x + radius > design_w or
                y - radius < 0 or y + radius > design_h):
            failed += 1
            continue

        shape = random.choice(SHAPES)
        candidate = (x, y, radius)

        if any(overlaps(candidate, (h[0], h[1], h[2]/2), sep) for h in holes):
            failed += 1
            continue

        holes.append((x, y, size, shape))
        failed = 0

    return holes


def export_preview(holes, design_w, design_h, output_path, scale=3.5):
    prev_w = int(design_w * scale)
    prev_h = int(design_h * scale)
    preview = Image.new("RGB", (prev_w, prev_h), color=(230, 230, 228))
    draw = ImageDraw.Draw(preview)

    for x, y, size, shape in holes:
        s = size * scale
        cx, cy = x * scale, y * scale
        half = s / 2.0

        if shape == "circle":
            draw.ellipse([cx-half, cy-half, cx+half, cy+half], fill=(25, 25, 28))
        elif shape == "square":
            draw.rectangle([cx-half, cy-half, cx+half, cy+half], fill=(25, 25, 28))
        else:  # triangle
            pts = [
                (cx, cy - half),
                (cx - half, cy + half * 0.8),
                (cx + half, cy + half * 0.8),
            ]
            draw.polygon(pts, fill=(25, 25, 28))

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

    for x, y, size, shape in holes:
        cx = FLANGE + x
        cy = FLANGE + y
        half = size / 2.0

        if shape == "circle":
            lines.extend([
                "0", "CIRCLE", "8", "PERFORACIONES",
                "10", f"{cx:.3f}", "20", f"{cy:.3f}", "30", "0.0",
                "40", f"{half:.3f}",
            ])
        elif shape == "square":
            x1, y1 = cx - half, cy - half
            x2, y2 = cx + half, cy + half
            add_line(x1, y1, x2, y1, "PERFORACIONES")
            add_line(x2, y1, x2, y2, "PERFORACIONES")
            add_line(x2, y2, x1, y2, "PERFORACIONES")
            add_line(x1, y2, x1, y1, "PERFORACIONES")
        else:  # triangle
            p1 = (cx, cy - half)
            p2 = (cx - half, cy + half * 0.8)
            p3 = (cx + half, cy + half * 0.8)
            add_line(p1[0], p1[1], p2[0], p2[1], "PERFORACIONES")
            add_line(p2[0], p2[1], p3[0], p3[1], "PERFORACIONES")
            add_line(p3[0], p3[1], p1[0], p1[1], "PERFORACIONES")

    lines.extend(["0", "ENDSEC", "0", "EOF"])
    with open(output_path, "w") as f:
        f.write("\n".join(lines))
    print(f"DXF: {output_path}")


def main(imagen, ancho=480, alto=560, salida="mixto", seed=42):
    print("=== Generador MIXTO (círculos + cuadrados + triángulos) ===")
    print(f"Imagen: {imagen}\n")

    img, design_w, design_h, px_per_mm = load_and_prepare(imagen, ancho, alto)
    print(f"Diseño: {design_w:.0f} x {design_h:.0f} mm")

    params = analyze_image(img)
    holes = generate_mixed(img, design_w, design_h, px_per_mm, params, seed=seed)

    counts = {"circle": 0, "square": 0, "triangle": 0}
    for h in holes:
        counts[h[3]] += 1

    print(f"Total: {len(holes)}  →  círculos:{counts['circle']}  cuadrados:{counts['square']}  triángulos:{counts['triangle']}")

    export_dxf(holes, f"{salida}.dxf")
    export_preview(holes, design_w, design_h, f"{salida}_preview.png")
    print("¡Listo!")


if __name__ == "__main__":
    main("perro.png", salida="perro_mixto")
