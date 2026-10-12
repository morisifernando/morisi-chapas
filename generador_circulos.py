#!/usr/bin/env python3
"""
Generador de diseño paramétrico de perforaciones circulares
a partir de una imagen JPG.

- Zonas oscuras → círculos más grandes (hasta 30 mm)
- Zonas claras  → círculos más chicos (desde 10 mm)
- Disposición aleatoria con separación mínima de 7 mm (borde a borde)
- Exporta DXF + preview PNG
"""

import argparse
import math
import random
from pathlib import Path

import cv2
import ezdxf
import numpy as np
from PIL import Image, ImageDraw


# ===================== PARÁMETROS =====================
DIAM_MIN = 10.0          # mm
DIAM_MAX = 30.0          # mm
SEP_MIN = 7.0            # mm borde a borde
SHEET_W = 2000.0         # mm
SHEET_H = 1000.0         # mm
FLANGE = 30.0            # mm aletas perimetrales
USABLE_W = SHEET_W - 2 * FLANGE   # 1940 mm
USABLE_H = SHEET_H - 2 * FLANGE   # 940 mm

# Control de densidad (cuántos intentos fallidos seguidos antes de parar)
MAX_FAILED_ATTEMPTS = 8000
MAX_CIRCLES = 2500       # límite de seguridad


def brightness_to_diameter(brightness: float) -> float:
    """
    brightness: 0.0 (negro) → 1.0 (blanco)
    Retorna diámetro en mm.
    Oscuro = grande, claro = chico.
    """
    # Invertimos: 0 (oscuro) → DIAM_MAX, 1 (claro) → DIAM_MIN
    t = 1.0 - brightness
    return DIAM_MIN + t * (DIAM_MAX - DIAM_MIN)


def load_and_prepare_image(path: str, target_w: float, target_h: float):
    """Carga la imagen, la convierte a escala de grises y la redimensiona
    manteniendo aspect ratio para que quepa en target_w x target_h (mm).
    Retorna la imagen en escala de grises (numpy) y el tamaño real usado (mm).
    """
    img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError(f"No se pudo cargar la imagen: {path}")

    h, w = img.shape
    aspect = w / h

    # Ajustar al área objetivo manteniendo proporción
    if target_w / target_h > aspect:
        # Limitado por altura
        design_h = target_h
        design_w = design_h * aspect
    else:
        design_w = target_w
        design_h = design_w / aspect

    # Redimensionar imagen a una resolución razonable para muestreo
    # (aprox 2-3 px por mm es suficiente)
    px_per_mm = 2.5
    img_w = int(design_w * px_per_mm)
    img_h = int(design_h * px_per_mm)
    img_resized = cv2.resize(img, (img_w, img_h), interpolation=cv2.INTER_AREA)

    return img_resized, design_w, design_h, px_per_mm


def get_local_brightness(img: np.ndarray, x_mm: float, y_mm: float,
                         px_per_mm: float, design_w: float, design_h: float) -> float:
    """Devuelve brillo normalizado 0-1 en la posición (x_mm, y_mm) del diseño."""
    # Convertir mm → píxeles
    px = int(x_mm * px_per_mm)
    py = int(y_mm * px_per_mm)

    h, w = img.shape
    if px < 0 or px >= w or py < 0 or py >= h:
        return 0.5  # valor neutro fuera de la imagen

    # Promedio en una pequeña ventana para suavizar
    r = 3
    x1 = max(0, px - r)
    x2 = min(w, px + r + 1)
    y1 = max(0, py - r)
    y2 = min(h, py + r + 1)
    patch = img[y1:y2, x1:x2]
    return float(np.mean(patch)) / 255.0


def circles_overlap(c1, c2, sep_min: float) -> bool:
    """c = (x, y, radius)"""
    x1, y1, r1 = c1
    x2, y2, r2 = c2
    dist = math.hypot(x1 - x2, y1 - y2)
    return dist < (r1 + r2 + sep_min)


def generate_circles(img: np.ndarray, design_w: float, design_h: float,
                     px_per_mm: float, seed: int | None = None):
    """Genera lista de círculos (x, y, diameter) en mm dentro del área de diseño."""
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)

    circles = []  # lista de (x, y, radius)
    failed = 0

    while failed < MAX_FAILED_ATTEMPTS and len(circles) < MAX_CIRCLES:
        # Posición aleatoria dentro del área de diseño
        x = random.uniform(0, design_w)
        y = random.uniform(0, design_h)

        brightness = get_local_brightness(img, x, y, px_per_mm, design_w, design_h)
        diam = brightness_to_diameter(brightness)
        radius = diam / 2.0

        # Verificar que el círculo completo quede dentro del área
        if (x - radius < 0 or x + radius > design_w or
                y - radius < 0 or y + radius > design_h):
            failed += 1
            continue

        candidate = (x, y, radius)

        # Verificar colisiones
        collision = False
        for existing in circles:
            if circles_overlap(candidate, existing, SEP_MIN):
                collision = True
                break

        if collision:
            failed += 1
            continue

        # Aceptado
        circles.append(candidate)
        failed = 0  # reset contador de fallos

    # Convertir a (x, y, diameter)
    result = [(x, y, r * 2) for x, y, r in circles]
    return result


def export_dxf(circles, design_w: float, design_h: float, output_path: str,
               offset_x: float = FLANGE, offset_y: float = FLANGE):
    """
    Exporta los círculos a DXF.
    Se colocan con offset para dejar las aletas perimetrales.
    También dibuja el contorno de la chapa y el área útil.
    """
    doc = ezdxf.new("R2010")  # compatible con la mayoría de máquinas
    msp = doc.modelspace()

    # Capa para perforaciones
    doc.layers.add("PERFORACIONES", color=1)  # rojo
    doc.layers.add("CONTORNO", color=3)       # verde
    doc.layers.add("AREA_UTIL", color=4)      # cian

    # Contorno de la chapa completa
    msp.add_lwpolyline(
        [(0, 0), (SHEET_W, 0), (SHEET_W, SHEET_H), (0, SHEET_H), (0, 0)],
        dxfattribs={"layer": "CONTORNO", "closed": True}
    )

    # Área útil (después de aletas)
    msp.add_lwpolyline(
        [(FLANGE, FLANGE),
         (FLANGE + USABLE_W, FLANGE),
         (FLANGE + USABLE_W, FLANGE + USABLE_H),
         (FLANGE, FLANGE + USABLE_H),
         (FLANGE, FLANGE)],
        dxfattribs={"layer": "AREA_UTIL", "closed": True}
    )

    # Círculos (perforaciones)
    for x, y, diam in circles:
        cx = offset_x + x
        cy = offset_y + y
        msp.add_circle(
            (cx, cy),
            radius=diam / 2.0,
            dxfattribs={"layer": "PERFORACIONES"}
        )

    doc.saveas(output_path)
    print(f"DXF guardado: {output_path}")


def export_preview(circles, design_w: float, design_h: float,
                   img: np.ndarray, px_per_mm: float, output_path: str,
                   scale: float = 2.0):
    """
    Genera un preview PNG de alta calidad.
    Fondo gris metalizado + círculos negros (perforaciones).
    """
    # Resolución del preview
    prev_w = int(design_w * scale)
    prev_h = int(design_h * scale)

    # Crear imagen de fondo (tono metal)
    preview = Image.new("RGB", (prev_w, prev_h), color=(180, 180, 185))
    draw = ImageDraw.Draw(preview)

    # Dibujar los círculos (perforaciones = negro)
    for x, y, diam in circles:
        r = (diam / 2.0) * scale
        cx = x * scale
        cy = y * scale
        bbox = [cx - r, cy - r, cx + r, cy + r]
        draw.ellipse(bbox, fill=(30, 30, 30), outline=(20, 20, 20))

    preview.save(output_path, quality=95)
    print(f"Preview guardado: {output_path}")
    return preview


def main():
    parser = argparse.ArgumentParser(description="Generador de perforaciones paramétricas")
    parser.add_argument("imagen", help="Ruta de la imagen JPG/PNG")
    parser.add_argument("--ancho", type=float, default=600.0,
                        help="Ancho máximo del diseño en mm (default 600)")
    parser.add_argument("--alto", type=float, default=400.0,
                        help="Alto máximo del diseño en mm (default 400)")
    parser.add_argument("--seed", type=int, default=None, help="Semilla aleatoria")
    parser.add_argument("--salida", default="salida", help="Prefijo de archivos de salida")
    args = parser.parse_args()

    print("=== Generador de perforaciones paramétricas ===")
    print(f"Imagen: {args.imagen}")
    print(f"Área objetivo: {args.ancho} x {args.alto} mm")
    print(f"Diámetros: {DIAM_MIN}-{DIAM_MAX} mm | Separación mín: {SEP_MIN} mm")
    print()

    # 1. Cargar y preparar imagen
    img, design_w, design_h, px_per_mm = load_and_prepare_image(
        args.imagen, args.ancho, args.alto
    )
    print(f"Diseño real: {design_w:.1f} x {design_h:.1f} mm")

    # 2. Generar círculos
    print("Generando círculos (esto puede tardar unos segundos)...")
    circles = generate_circles(img, design_w, design_h, px_per_mm, seed=args.seed)
    print(f"Círculos generados: {len(circles)}")

    if not circles:
        print("No se generaron círculos. Revisá la imagen o los parámetros.")
        return

    # Estadísticas
    diams = [d for _, _, d in circles]
    print(f"Diámetro promedio: {np.mean(diams):.1f} mm")
    print(f"Diámetro mín/máx: {min(diams):.1f} / {max(diams):.1f} mm")

    # 3. Exportar
    out_dir = Path(args.salida).parent
    out_dir.mkdir(parents=True, exist_ok=True)

    dxf_path = f"{args.salida}.dxf"
    preview_path = f"{args.salida}_preview.png"

    export_dxf(circles, design_w, design_h, dxf_path)
    export_preview(circles, design_w, design_h, img, px_per_mm, preview_path)

    print("\n¡Listo!")
    print(f"  - DXF:     {dxf_path}")
    print(f"  - Preview: {preview_path}")


if __name__ == "__main__":
    main()
