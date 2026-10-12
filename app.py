#!/usr/bin/env python3
"""
Chapas Perforadas Morisi – Bandejas perforadas a medida.
Incluye potenciómetro de detalle (tamaño / cantidad de perforaciones).
Ejecutar:  streamlit run app.py
"""

import io
import math
import random

import numpy as np
import streamlit as st
from PIL import Image, ImageDraw, ImageOps, ImageFilter, ImageEnhance

import json as _json
import os as _os

_CONFIG_PATH = _os.path.join(_os.path.dirname(__file__), "precios_config.json")

def _load_config():
    defaults = {
        "admin_user": "morisi",
        "admin_pass": "morisi2026",
        "contacto": {
            "email_taller": "pedidos@morisi.com",
            "whatsapp_taller": "5491112345678",
            "nombre_taller": "Morisi Chapas Perforadas",
        },
        "cobro": {
            "banco": "",
            "titular": "",
            "cbu": "",
            "alias": "",
            "cuit": "",
            "mercado_pago_link": "",
            "acepta_transferencia": True,
            "acepta_mercado_pago": True,
            "acepta_efectivo_retiro": True,
            "nota_pago": "Una vez acreditado el pago, coordinamos producción y entrega.",
        },
        "precios": {
            "material_m2": 8500,
            "corte_por_minuto": 120,
            "velocidad_mm_s": 20,
            "pintura_m2": 3200,
            "pintura_caras": 1,
            "plegado_ml": 1500,
            "plegado_fijo": 500,
            "embalaje_m2": 400,
            "embalaje_fijo": 300,
            "setup": 1500,
            "margen_pct": 30,
            "despacho_base": 2500,
            "despacho_por_km": 180,
            "despacho_km_min": 5,
            "zonas": {"CABA": 3500, "GBA": 5500, "Interior": 12000},
        },
    }
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = _json.load(f)
        if "precios" in data:
            defaults["admin_user"] = data.get("admin_user", defaults["admin_user"])
            defaults["admin_pass"] = data.get("admin_pass", defaults["admin_pass"])
            defaults["precios"].update(data["precios"])
            if "zonas" in data["precios"]:
                defaults["precios"]["zonas"] = data["precios"]["zonas"]
        if "contacto" in data and isinstance(data["contacto"], dict):
            defaults["contacto"].update(data["contacto"])
        if "cobro" in data and isinstance(data["cobro"], dict):
            defaults["cobro"].update(data["cobro"])
        return defaults
    except Exception:
        return defaults

def _save_config(cfg):
    with open(_CONFIG_PATH, "w", encoding="utf-8") as f:
        _json.dump(cfg, f, indent=2, ensure_ascii=False)

_CFG = _load_config()
PRECIOS = _CFG["precios"]
ADMIN_USER = _CFG["admin_user"]
ADMIN_PASS = _CFG["admin_pass"]
CONTACTO = _CFG.get("contacto", {
    "email_taller": "pedidos@morisi.com",
    "whatsapp_taller": "5491112345678",
    "nombre_taller": "Morisi Chapas Perforadas",
})
COBRO = _CFG.get("cobro", {
    "banco": "", "titular": "", "cbu": "", "alias": "", "cuit": "",
    "mercado_pago_link": "",
    "acepta_transferencia": True,
    "acepta_mercado_pago": True,
    "acepta_efectivo_retiro": True,
    "nota_pago": "Una vez acreditado el pago, coordinamos producción y entrega.",
})

MEDIDAS = {
    "1,2 × 2,4 m": (1200, 2400),
    "1,2 × 1,2 m": (1200, 1200),
    "1,2 × 0,6 m": (1200, 600),
    "0,6 × 0,6 m": (600, 600),
    "Personalizado": None,
}

st.set_page_config(page_title="Chapas Perforadas Morisi", page_icon="◆", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', system-ui, sans-serif; }
/* Morisi: naranja 70% · negro 15% · blanco 15% */
.stApp {
    background: linear-gradient(165deg, #1a0f08 0%, #2a1810 35%, #1c1008 100%);
    color: #fff8f2;
}
h1, h2, h3 {
    font-family: 'Inter', system-ui, sans-serif !important;
    color: #ffffff !important; font-weight: 700 !important;
}
.stCaption, small, [data-testid="stCaption"] { color: #e8b896 !important; }
/* Primary = naranja Morisi */
.stButton > button[kind="primary"] {
    background: #ff7814 !important; color: #ffffff !important;
    border: none !important; border-radius: 10px !important;
    font-weight: 600 !important; padding: 0.75rem 1.5rem !important;
    box-shadow: 0 4px 16px rgba(255,120,20,0.4) !important;
}
.stButton > button[kind="primary"]:hover {
    background: #ff8c33 !important;
}
.stButton > button {
    border-radius: 10px !important;
    border: 1px solid rgba(255,255,255,0.2) !important;
    background: rgba(0,0,0,0.35) !important; color: #fff8f2 !important;
}
div[data-testid="stMetric"] {
    background: rgba(0,0,0,0.35); border: 1px solid rgba(255,120,20,0.25);
    border-radius: 14px; padding: 14px;
}
.price-box {
    background: rgba(0,0,0,0.4);
    border: 1px solid rgba(255,120,20,0.35); border-radius: 16px;
    padding: 1.5rem 1.6rem; margin-top: 0.6rem;
}
.price-box .label {
    font-size: 0.68rem; letter-spacing: 0.14em; text-transform: uppercase;
    color: #ff7814;
}
.price-box .amount {
    font-size: 2.5rem; font-weight: 700; color: #ffffff; margin-top: 4px;
}
.price-box .note { font-size: 0.82rem; color: #e8b896; margin-top: 0.6rem; }
.step-bar {
    display: flex; justify-content: center; gap: 8px; flex-wrap: wrap;
    margin: 0.3rem 0 1rem 0; padding: 0.5rem;
}
.step-pill {
    display: inline-flex; align-items: center; gap: 8px;
    padding: 8px 14px; border-radius: 999px;
    background: rgba(0,0,0,0.35); border: 1px solid rgba(255,120,20,0.3);
    font-size: 0.78rem; color: #e8b896; font-weight: 500;
}
.step-pill .num {
    width: 22px; height: 22px; border-radius: 50%;
    display: inline-flex; align-items: center; justify-content: center;
    font-size: 0.72rem; font-weight: 700; color: #1a0f08;
}
.step-pill.on { border-color: #ff7814; color: #ffffff; background: rgba(255,120,20,0.18); }
.card-ctrl {
    background: rgba(0,0,0,0.35); border: 1px solid rgba(255,120,20,0.25);
    border-radius: 14px; padding: 14px 16px; margin-bottom: 10px;
}
.card-ctrl h4 {
    margin: 0 0 6px 0; font-size: 0.85rem; color: #ff7814 !important;
    font-family: Inter, sans-serif !important; font-weight: 600 !important;
}
.preview-frame {
    background: #ffffff; border-radius: 16px; padding: 12px;
    box-shadow: 0 16px 48px rgba(0,0,0,0.45);
    border: 1px solid rgba(255,120,20,0.2);
}
.hero-upload {
    text-align: center; padding: 3rem 1.5rem;
    background: rgba(0,0,0,0.3);
    border: 1px dashed rgba(255,120,20,0.5); border-radius: 20px; margin: 1.5rem 0;
}
.brand-tag {
    font-size: 0.7rem; letter-spacing: 0.16em; text-transform: uppercase;
    color: #ff7814; font-weight: 600;
}
.stRadio label, .stSelectbox label { color: #fff8f2 !important; }
#MainMenu, footer, header { visibility: hidden; }
section[data-testid="stSidebar"] { display: none; }
</style>
""", unsafe_allow_html=True)




def enhance_image(pil_img):
    img = pil_img.convert("L")
    img = ImageOps.autocontrast(img, cutoff=1)
    img = ImageEnhance.Contrast(img).enhance(1.35)
    img = img.filter(ImageFilter.UnsharpMask(radius=1.2, percent=120, threshold=2))
    return img


def detalle_a_params(nivel: int):
    """
    Potenciómetro 1–10:
      1 = grueso (agujeros grandes, pocos, imagen más abstracta)
     10 = fino   (agujeros chicos, muchos, se nota más la imagen)
    """
    t = (nivel - 1) / 9.0  # 0..1
    # Más separación = menos costo de láser; la imagen sigue legible
    # diámetros: grueso ~6–12 mm → fino ~3–8 mm
    dmin = 6.0 - t * 3.0
    dmax = 12.0 - t * 4.5
    # separación entre bordes de agujeros ~7 mm
    sep = 7.0
    # paso de grilla: ~14–16 mm entre centros
    step = 16.0 - t * 2.0
    return dmin, dmax, sep, step


def generate_calado(pil_img, design_w, design_h, nivel=6):
    """
    Calado estilo silueta metálica:
    - Metal sólido + cortes internos limpios
    - Muchos puentes finos repartidos en el contorno (disimulados)
    - Una sola pieza
    """
    from scipy import ndimage

    t = (nivel - 1) / 9.0
    w = max(220, int(design_w * 0.38))
    h = max(220, int(design_h * 0.38))

    g = enhance_image(pil_img)
    g = ImageEnhance.Contrast(g).enhance(2.2)
    g = ImageEnhance.Sharpness(g).enhance(1.5)
    g = g.resize((w, h), Image.Resampling.LANCZOS)
    # blur leve: contorno suave sin borrar la figura
    g = g.filter(ImageFilter.GaussianBlur(radius=0.8))
    arr = np.array(g).astype(np.float32) / 255.0

    thr = max(0.32, min(0.58, float(np.percentile(arr, 48 - t * 6))))
    solid = (arr < thr).astype(np.uint8)
    solid = ndimage.binary_fill_holes(solid).astype(np.uint8)
    # morfología fina → más detalle de hojas/ramas
    solid = ndimage.binary_closing(solid, structure=np.ones((3, 3))).astype(np.uint8)
    solid = ndimage.binary_opening(solid, structure=np.ones((2, 2))).astype(np.uint8)
    solid = ndimage.binary_closing(solid, structure=np.ones((3, 3))).astype(np.uint8)
    soft = ndimage.gaussian_filter(solid.astype(np.float32), sigma=0.65)
    solid = (soft > 0.4).astype(np.uint8)

    labeled, nlab = ndimage.label(solid)
    if nlab > 0:
        sizes = ndimage.sum(solid, labeled, range(1, nlab + 1))
        solid = (labeled == (int(np.argmax(sizes)) + 1)).astype(np.uint8)

    inside = solid.astype(bool)
    gy, gx = np.gradient(arr)
    grad = np.sqrt(gx * gx + gy * gy)
    g_thr = float(np.percentile(grad[inside], 75)) if inside.any() else 0.1
    cut = (((arr > thr + 0.08) & inside) | ((grad > g_thr) & inside)).astype(np.uint8)
    cut = ndimage.binary_dilation(cut, iterations=1).astype(np.uint8)
    cut = ndimage.binary_closing(cut, structure=np.ones((3, 3))).astype(np.uint8)
    cut = cut & ndimage.binary_erosion(solid, iterations=4).astype(np.uint8)
    clab, cn = ndimage.label(cut)
    if cn > 0:
        csizes = ndimage.sum(cut, clab, range(1, cn + 1))
        min_c = max(12, int(0.0004 * w * h))
        for i, s in enumerate(csizes, 1):
            if s < min_c:
                cut[clab == i] = 0

    metal = solid.copy()
    metal[cut > 0] = 0
    outer_ring = solid & (~ndimage.binary_erosion(solid, iterations=3))
    metal[outer_ring > 0] = 1

    b = max(3, int(0.022 * min(w, h)))
    metal[:b, :] = 1
    metal[-b:, :] = 1
    metal[:, :b] = 1
    metal[:, -b:] = 1

    bridge_mm = max(5.0, min(6.5, 5.5))
    bridge_r = max(1, int(round(bridge_mm * 0.38 / 2.0)))

    def add_bridge(mask, y0, x0, y1, x1, radius):
        dy, dx = abs(y1 - y0), abs(x1 - x0)
        sy = 1 if y0 < y1 else -1
        sx = 1 if x0 < x1 else -1
        err = dx - dy
        y, x = y0, x0
        hh, ww = mask.shape
        while True:
            mask[max(0, y - radius):min(hh, y + radius + 1),
                 max(0, x - radius):min(ww, x + radius + 1)] = 1
            if (y, x) == (y1, x1):
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy

    def nearest_points(comp_a, comp_b):
        dist = ndimage.distance_transform_edt(~comp_a)
        ys, xs = np.where(comp_b)
        if len(ys) == 0:
            return None
        i = int(np.argmin(dist[ys, xs]))
        y1, x1 = int(ys[i]), int(xs[i])
        y, x = y1, x1
        for _ in range(h + w):
            if comp_a[y, x]:
                return (y, x, y1, x1)
            bestv = dist[y, x]
            ny, nx = y, x
            for dy_ in (-1, 0, 1):
                for dx_ in (-1, 0, 1):
                    yy, xx = y + dy_, x + dx_
                    if 0 <= yy < h and 0 <= xx < w and dist[yy, xx] < bestv:
                        bestv, ny, nx = dist[yy, xx], yy, xx
            if (ny, nx) == (y, x):
                break
            y, x = ny, nx
        return (y, x, y1, x1)

    for _ in range(80):
        labeled, nlab = ndimage.label(metal)
        if nlab <= 1:
            break
        sizes = sorted([(int((labeled == lab).sum()), lab) for lab in range(1, nlab + 1)], reverse=True)
        main = labeled == sizes[0][1]
        pts = nearest_points(main, labeled == sizes[1][1])
        if pts:
            add_bridge(metal, pts[0], pts[1], pts[2], pts[3], bridge_r)

    # ~12 puentes figura→marco repartidos en el contorno
    frame_mask = (
        (np.arange(h)[:, None] < b) | (np.arange(h)[:, None] >= h - b) |
        (np.arange(w)[None, :] < b) | (np.arange(w)[None, :] >= w - b)
    )
    dist_to_frame = ndimage.distance_transform_edt(~frame_mask)
    fig = solid.astype(bool)
    edge_fig = fig & (~ndimage.binary_erosion(fig, iterations=2))
    ys, xs = np.where(edge_fig & (metal > 0))
    if len(ys) > 20:
        cy, cx = float(ys.mean()), float(xs.mean())
        for k in range(12):
            ang = 2 * np.pi * k / 12
            best_i, best_score = 0, -1e9
            step = max(1, len(ys) // 200)
            for i in range(0, len(ys), step):
                score = (ys[i] - cy) * np.sin(ang) + (xs[i] - cx) * np.cos(ang)
                if score > best_score:
                    best_score, best_i = score, i
            y1, x1 = int(ys[best_i]), int(xs[best_i])
            y, x = y1, x1
            for _ in range(h + w):
                if frame_mask[y, x]:
                    break
                bestv = dist_to_frame[y, x]
                ny, nx = y, x
                for dy_ in (-1, 0, 1):
                    for dx_ in (-1, 0, 1):
                        yy, xx = y + dy_, x + dx_
                        if 0 <= yy < h and 0 <= xx < w and dist_to_frame[yy, xx] < bestv:
                            bestv, ny, nx = dist_to_frame[yy, xx], yy, xx
                if (ny, nx) == (y, x):
                    break
                y, x = ny, nx
            add_bridge(metal, y, x, y1, x1, bridge_r)

    metal[:b, :] = 1
    metal[-b:, :] = 1
    metal[:, :b] = 1
    metal[:, -b:] = 1

    for _ in range(40):
        labeled, nlab = ndimage.label(metal)
        if nlab <= 1:
            break
        sizes = sorted([(int((labeled == lab).sum()), lab) for lab in range(1, nlab + 1)], reverse=True)
        main = labeled == sizes[0][1]
        pts = nearest_points(main, labeled == sizes[1][1])
        if pts:
            add_bridge(metal, pts[0], pts[1], pts[2], pts[3], bridge_r)

    h_edges = np.count_nonzero(metal[:, 1:] != metal[:, :-1])
    v_edges = np.count_nonzero(metal[1:, :] != metal[:-1, :])
    perimeter_mm = float(h_edges + v_edges) * (design_w / max(w, 1))

    return metal.astype(np.uint8), 1.0, perimeter_mm, thr, bridge_mm



def generate_holes(pil_img, design_w, design_h, forma="circulos", nivel=6, seed=42, invert=False, filtro="normal", zoom=1.0):
    """
    invert=False (POSITIVO): zonas claras → agujeros más grandes
    invert=True  (NEGATIVO): zonas oscuras → agujeros más grandes
    filtro: normal | contraste | suave | contorno | relieve | nitidez | punch | pixel | trama
    """
    if forma == "calado":
        mask, px, perim, thr, bridge_mm = generate_calado(pil_img, design_w, design_h, nivel)
        return [], 0.0, 0.0, {
            "calado": True,
            "mask": mask,
            "px": px,
            "perimeter_mm": perim,
            "bridge_mm": bridge_mm,
        }

    dmin, dmax, sep, step = detalle_a_params(nivel)
    # Ajustes por filtro (sobre el detalle base del potenciómetro)
    if filtro == "contraste":
        dmin, dmax, sep = dmin * 0.85, dmax * 1.15, sep * 0.95
        contrast_boost, thr_skip = 2.1, 0.12
    elif filtro == "suave":
        dmin, dmax, sep = dmin * 1.1, dmax * 0.9, sep * 1.1
        contrast_boost, thr_skip = 0.85, 0.22
    elif filtro == "contorno":
        dmin, dmax, sep = dmin * 0.75, dmax * 1.05, sep * 0.9
        contrast_boost, thr_skip = 1.5, 0.08
    elif filtro == "relieve":
        dmin, dmax, sep = dmin * 0.8, dmax * 1.2, sep * 0.95
        contrast_boost, thr_skip = 1.55, 0.10
    elif filtro == "nitidez":
        dmin, dmax, sep, step = dmin * 0.7, dmax * 0.85, sep * 0.8, step * 0.8
        contrast_boost, thr_skip = 1.85, 0.10
    elif filtro == "punch":
        dmin, dmax, sep = dmin * 0.7, dmax * 1.3, sep * 0.95
        contrast_boost, thr_skip = 2.4, 0.28
    elif filtro == "pixel":
        dmin, dmax, sep, step = max(5.0, dmin * 1.6), dmax * 1.6, sep * 1.3, step * 1.7
        contrast_boost, thr_skip = 1.3, 0.15
    elif filtro == "trama":
        dmin, dmax, sep, step = dmin * 0.85, dmax * 0.9, sep * 0.85, step * 0.85
        contrast_boost, thr_skip = 1.35, 0.18
    else:
        contrast_boost, thr_skip = 1.0, 0.20

    img_enh = enhance_image(pil_img)
    if contrast_boost != 1.0:
        from PIL import ImageEnhance as _IE
        img_enh = _IE.Contrast(img_enh).enhance(contrast_boost)

    allowed = {
        "circulos": ["circle"],
        "cuadrados": ["square"],
        "triangulos": ["triangle"],
        "mixto": ["circle", "square", "triangle"],
    }.get(forma, ["circle"])

    random.seed(seed)
    holes = []

    margin = max(15.0, dmax + 2.0)
    # --- Cubrir la chapa (cover) + zoom del cliente ---
    # La foto llena todo el área útil (se recorta lo que sobra).
    # zoom 1.0 = justo para llenar · >1 agranda (más zoom) · <1 achica (puede verse borde).
    content_w = design_w - 2 * margin
    content_h = design_h - 2 * margin
    ox = margin
    oy = margin
    zoom = max(0.5, min(2.5, float(zoom)))

    iw, ih = img_enh.size
    img_aspect = iw / max(ih, 1)
    sheet_aspect = content_w / max(content_h, 1.0)
    # Escala base: cubrir el área (cover)
    if img_aspect > sheet_aspect:
        # imagen más ancha → ajusta por alto y recorta lados
        base_h = content_h
        base_w = content_h * img_aspect
    else:
        # imagen más alta → ajusta por ancho y recorta arriba/abajo
        base_w = content_w
        base_h = content_w / img_aspect
    # Aplicar zoom (centrado)
    view_w = base_w / zoom
    view_h = base_h / zoom
    # Origen de la ventana de muestreo en coords de imagen normalizadas
    # Centro de la chapa mapea al centro de la foto
    # u,v en [0,1] sobre la foto: centro = 0.5
    # A cada punto (x,y) de la chapa le corresponde offset desde el centro del panel

    px_per_mm = 2.5
    arr = np.array(img_enh.resize(
        (max(60, int(base_w * px_per_mm)), max(60, int(base_h * px_per_mm))),
        Image.Resampling.LANCZOS,
    )).astype(float) / 255.0
    if invert:
        arr = 1.0 - arr

    pitch = max(step, dmax + sep)
    gy, gx = np.gradient(arr)
    grad = np.sqrt(gx * gx + gy * gy)
    gmax = float(grad.max()) + 1e-6

    def sample_bg(x, y):
        # posición relativa al centro del área útil (-0.5 .. 0.5)
        rx = (x - (ox + content_w / 2.0)) / content_w
        ry = (y - (oy + content_h / 2.0)) / content_h
        # ventana de la foto centrada, tamaño 1/zoom del cover
        # cover: la foto cubre el panel; zoom acerca
        u = 0.5 + rx / zoom
        v = 0.5 - ry / zoom  # Y invertida: arriba foto = arriba chapa
        # clamp a bordes de la foto (si zoom < 1 puede haber fuera → metal sin foto)
        if u < 0.0 or u > 1.0 or v < 0.0 or v > 1.0:
            return 0.0, 0.0  # fuera de la foto = macizo (sin agujero)
        px = int(u * (arr.shape[1] - 1))
        py = int(v * (arr.shape[0] - 1))
        return float(arr[py, px]), float(grad[py, px])

    row = 0
    y = margin
    while y <= design_h - margin:
        col = 0
        x = margin
        while x <= design_w - margin:
            b, g = sample_bg(x, y)
            gn = g / gmax

            if filtro == "contorno":
                if gn < 0.04 and b > 0.55:
                    x += pitch; col += 1; continue
                t = max(0.0, min(1.0, 0.35 * b + 0.65 * min(1.0, gn * 3)))
            elif filtro == "relieve":
                if b < thr_skip and gn < 0.05:
                    x += pitch; col += 1; continue
                t = max(0.0, min(1.0, b * 0.5 + gn * 0.9))
            elif filtro == "punch":
                if b < 0.42:
                    x += pitch; col += 1; continue
                t = 1.0 if b > 0.68 else 0.32
            else:
                if b < thr_skip:
                    x += pitch; col += 1; continue
                if g < 0.025 and (row + col) % 2 == 1 and filtro not in ("nitidez", "trama"):
                    x += pitch; col += 1; continue
                if g < 0.015 and b > 0.70 and (row + col) % 3 != 0:
                    x += pitch; col += 1; continue
                t = max(0.0, min(1.0, (b - thr_skip) / max(0.01, 1.0 - thr_skip)))

            size = dmin + t * (dmax - dmin)
            size = min(size, pitch - sep)
            if filtro == "pixel":
                size = round(size / 3.0) * 3.0
            if size >= max(2.5, dmin * 0.75):
                holes.append((float(x), float(y), float(size), random.choice(allowed)))
            x += pitch
            col += 1
        y += pitch
        row += 1

    return holes, dmin, dmax, None


def render_preview(holes, design_w, design_h, color_name="Negro", scale=None, calado_info=None, tecnico=False):
    # tecnico=True → vista de trabajo: chapa blanca + perforaciones negras (se actualiza al tocar controles)
    if tecnico:
        bg, fg = (245, 245, 242), (12, 12, 12)
    elif color_name == "Blanco":
        bg, fg = (40, 40, 38), (230, 230, 225)
    elif color_name == "Gris":
        bg, fg = (36, 36, 34), (180, 180, 175)
    elif color_name == "Oro":
        bg, fg = (42, 34, 18), (200, 165, 85)
    elif color_name == "Plata":
        bg, fg = (30, 34, 42), (170, 185, 205)
    elif color_name == "Frío":
        bg, fg = (28, 32, 42), (140, 160, 190)
    else:
        bg, fg = (32, 32, 30), (220, 218, 210)

    # Escala según tamaño de chapa (máx ~900 px en el lado largo)
    if scale is None:
        scale = min(2.6, 900.0 / max(design_w, design_h))
    w, h = max(1, int(design_w * scale)), max(1, int(design_h * scale))
    img = Image.new("RGB", (w, h), bg)

    # --- CALADO: silueta sólida marcada ---
    if calado_info and calado_info.get("calado"):
        mask = calado_info["mask"]
        mh, mw = mask.shape
        # pintar figura (mask=1) con color fg sobre bg
        mask_img = Image.fromarray((mask * 255).astype(np.uint8), mode="L")
        mask_img = mask_img.resize((w, h), Image.Resampling.NEAREST)
        m = np.array(mask_img) > 127
        arr = np.array(img)
        arr[m] = fg
        return Image.fromarray(arr)

    draw = ImageDraw.Draw(img)
    for x, y, size, shape in holes:
        s = size * scale
        # y en diseño: origen abajo → en pantalla invertimos
        cx, cy = x * scale, (design_h - y) * scale
        half = s / 2
        if shape == "circle":
            draw.ellipse([cx - half, cy - half, cx + half, cy + half], fill=fg)
        elif shape == "square":
            draw.rectangle([cx - half, cy - half, cx + half, cy + half], fill=fg)
        else:
            draw.polygon(
                [(cx, cy - half), (cx - half, cy + half * 0.8), (cx + half, cy + half * 0.8)],
                fill=fg,
            )
    return img


def precio_final(holes, design_w, design_h, despacho_metodo="retiro", km=0, zona="CABA", calado_info=None):
    total_cut = 2 * (design_w + design_h)
    area_m2 = (design_w * design_h) / 1_000_000
    if calado_info and calado_info.get("calado"):
        total_cut += float(calado_info.get("perimeter_mm", 0))
    else:
        for _, _, size, shape in holes:
            if shape == "circle":
                total_cut += math.pi * size
            elif shape == "square":
                total_cut += 4 * size
            else:
                total_cut += 3 * size
    tiempo_min = (total_cut / PRECIOS["velocidad_mm_s"]) / 60
    metros_plegado = 2 * ((design_w + design_h) / 1000)
    costo = (
        area_m2 * PRECIOS["material_m2"]
        + tiempo_min * PRECIOS["corte_por_minuto"]
        + area_m2 * PRECIOS["pintura_caras"] * PRECIOS["pintura_m2"]
        + metros_plegado * PRECIOS["plegado_ml"] + PRECIOS["plegado_fijo"]
        + area_m2 * PRECIOS["embalaje_m2"] + PRECIOS["embalaje_fijo"]
        + PRECIOS["setup"]
    )
    subtotal = costo * (1 + PRECIOS["margen_pct"] / 100)
    if despacho_metodo == "retiro":
        c_desp = 0
    elif despacho_metodo == "distancia":
        c_desp = PRECIOS["despacho_base"] + max(km, PRECIOS["despacho_km_min"]) * PRECIOS["despacho_por_km"]
    else:
        c_desp = PRECIOS["zonas"].get(zona, 0)
    return {
        "total": round(subtotal + c_desp, 2),
        "agujeros": len(holes),
        "area_m2": round(area_m2, 4),
        "peso_kg": round(area_m2 * 9.42, 2),
        "tiempo_min": round(tiempo_min, 2),
    }


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------
import os as _os
_ASSETS = _os.path.join(_os.path.dirname(__file__), "assets")
_THUMBS = {
    "Negro": _os.path.join(_ASSETS, "thumb_negro.png"),
    "Gris": _os.path.join(_ASSETS, "thumb_gris.png"),
    "Blanco": _os.path.join(_ASSETS, "thumb_blanco.png"),
}
_RENDERS = {
    "Negro": _os.path.join(_ASSETS, "render_negro.png"),
    "Gris": _os.path.join(_ASSETS, "render_gris.png"),
    "Blanco": _os.path.join(_ASSETS, "render_blanco.png"),
}

# ===================== PANEL ADMIN (precios) =====================
# Acceso: en la URL agregá  ?admin=1   o elegí "Admin" abajo
_params = st.query_params
_want_admin = str(_params.get("admin", "")).lower() in ("1", "true", "yes")

if "admin_ok" not in st.session_state:
    st.session_state.admin_ok = False

_nav = st.radio(
    "nav",
    ["Cliente", "Admin precios"],
    horizontal=True,
    label_visibility="collapsed",
    index=1 if _want_admin else 0,
    key="nav_mode",
)

if _nav == "Admin precios":
    st.markdown("## Panel de precios · Morisi")
    st.caption("Solo personal autorizado · los clientes no ven estos valores")
    if not st.session_state.admin_ok:
        u = st.text_input("Usuario", value="")
        pw = st.text_input("Contraseña", type="password", value="")
        if st.button("Entrar", type="primary"):
            if u == ADMIN_USER and pw == ADMIN_PASS:
                st.session_state.admin_ok = True
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos")
        st.stop()

    st.success("Sesión admin activa")
    if st.button("Cerrar sesión"):
        st.session_state.admin_ok = False
        st.rerun()

    st.markdown("### Cargar / editar precios")
    c1, c2 = st.columns(2)
    with c1:
        material_m2 = st.number_input("Material ($ / m²)", min_value=0.0, value=float(PRECIOS.get("material_m2", 0)), step=100.0)
        corte_por_minuto = st.number_input("Corte láser ($ / minuto)", min_value=0.0, value=float(PRECIOS.get("corte_por_minuto", 0)), step=10.0)
        velocidad_mm_s = st.number_input("Velocidad de corte (mm / segundo)", min_value=1.0, value=float(PRECIOS.get("velocidad_mm_s", 20)), step=1.0)
        pintura_m2 = st.number_input("Pintura ($ / m²)", min_value=0.0, value=float(PRECIOS.get("pintura_m2", 0)), step=100.0)
        pintura_caras = st.number_input("Caras de pintura (1 o 2)", min_value=1, max_value=2, value=int(PRECIOS.get("pintura_caras", 1)), step=1)
        plegado_ml = st.number_input("Plegado ($ / metro lineal)", min_value=0.0, value=float(PRECIOS.get("plegado_ml", 0)), step=50.0)
        plegado_fijo = st.number_input("Plegado fijo ($ / pieza)", min_value=0.0, value=float(PRECIOS.get("plegado_fijo", 0)), step=50.0)
    with c2:
        embalaje_m2 = st.number_input("Embalaje ($ / m²)", min_value=0.0, value=float(PRECIOS.get("embalaje_m2", 0)), step=50.0)
        embalaje_fijo = st.number_input("Embalaje fijo ($ / unidad)", min_value=0.0, value=float(PRECIOS.get("embalaje_fijo", 0)), step=50.0)
        setup = st.number_input("Setup / preparación ($ / pedido)", min_value=0.0, value=float(PRECIOS.get("setup", 0)), step=100.0)
        margen_pct = st.number_input("Margen de ganancia (%)", min_value=0.0, value=float(PRECIOS.get("margen_pct", 0)), step=1.0)
        despacho_base = st.number_input("Despacho base ($)", min_value=0.0, value=float(PRECIOS.get("despacho_base", 0)), step=100.0)
        despacho_por_km = st.number_input("Despacho ($ / km)", min_value=0.0, value=float(PRECIOS.get("despacho_por_km", 0)), step=10.0)
        despacho_km_min = st.number_input("Km mínimos cobrados", min_value=0.0, value=float(PRECIOS.get("despacho_km_min", 0)), step=1.0)

    st.markdown("#### Zonas de entrega ($ fijo)")
    zcols = st.columns(3)
    zonas = dict(PRECIOS.get("zonas", {}))
    zkeys = list(zonas.keys()) or ["CABA", "GBA", "Interior"]
    new_zonas = {}
    for i, zk in enumerate(zkeys):
        with zcols[i % 3]:
            new_zonas[zk] = st.number_input(f"Zona {zk}", min_value=0.0, value=float(zonas.get(zk, 0)), step=100.0, key=f"z_{zk}")

    st.markdown("### Contacto del taller")
    st.caption("Acá llega el DXF y el comprobante cuando el cliente compra")
    email_taller = st.text_input("Email del taller (DXF + comprobante)", value=str(CONTACTO.get("email_taller", "")))
    whatsapp_taller = st.text_input(
        "WhatsApp del taller (con código de país, sin + ni espacios)",
        value=str(CONTACTO.get("whatsapp_taller", "")),
        help="Ejemplo Argentina: 5491112345678",
    )
    nombre_taller = st.text_input("Nombre del taller", value=str(CONTACTO.get("nombre_taller", "Morisi Chapas Perforadas")))

    st.markdown("### Cuenta donde entra el dinero")
    st.caption("Datos bancarios · el cliente los ve al elegir transferencia")
    banco = st.text_input("Banco", value=str(COBRO.get("banco", "")))
    titular = st.text_input("Titular de la cuenta", value=str(COBRO.get("titular", "")))
    cbu = st.text_input("CBU (22 dígitos)", value=str(COBRO.get("cbu", "")))
    alias = st.text_input("Alias CBU", value=str(COBRO.get("alias", "")))
    cuit = st.text_input("CUIT / CUIL", value=str(COBRO.get("cuit", "")))

    st.markdown("### Formas de cobro")
    acepta_transferencia = st.checkbox("Transferencia bancaria (CBU / Alias)", value=bool(COBRO.get("acepta_transferencia", True)))
    acepta_mercado_pago = st.checkbox("Mercado Pago (tarjeta, débito, dinero en cuenta)", value=bool(COBRO.get("acepta_mercado_pago", True)))
    mercado_pago_link = st.text_input(
        "Link de pago Mercado Pago",
        value=str(COBRO.get("mercado_pago_link", "")),
        help="Creá un link en Mercado Pago y pegalo acá. Las tarjetas se cargan en Mercado Pago, no en esta app.",
    )
    acepta_efectivo_retiro = st.checkbox("Efectivo al retirar en el taller", value=bool(COBRO.get("acepta_efectivo_retiro", True)))
    nota_pago = st.text_area(
        "Nota que ve el cliente al pagar",
        value=str(COBRO.get("nota_pago", "Una vez acreditado el pago, coordinamos producción y entrega.")),
        height=70,
    )

    if st.button("Guardar precios, contacto y cobro", type="primary"):
        new_p = {
            "material_m2": material_m2,
            "corte_por_minuto": corte_por_minuto,
            "velocidad_mm_s": velocidad_mm_s,
            "pintura_m2": pintura_m2,
            "pintura_caras": int(pintura_caras),
            "plegado_ml": plegado_ml,
            "plegado_fijo": plegado_fijo,
            "embalaje_m2": embalaje_m2,
            "embalaje_fijo": embalaje_fijo,
            "setup": setup,
            "margen_pct": margen_pct,
            "despacho_base": despacho_base,
            "despacho_por_km": despacho_por_km,
            "despacho_km_min": despacho_km_min,
            "zonas": new_zonas,
        }
        new_c = {
            "email_taller": email_taller.strip(),
            "whatsapp_taller": "".join(ch for ch in whatsapp_taller if ch.isdigit()),
            "nombre_taller": nombre_taller.strip() or "Morisi Chapas Perforadas",
        }
        new_cobro = {
            "banco": banco.strip(),
            "titular": titular.strip(),
            "cbu": "".join(ch for ch in cbu if ch.isdigit()),
            "alias": alias.strip(),
            "cuit": cuit.strip(),
            "mercado_pago_link": mercado_pago_link.strip(),
            "acepta_transferencia": bool(acepta_transferencia),
            "acepta_mercado_pago": bool(acepta_mercado_pago),
            "acepta_efectivo_retiro": bool(acepta_efectivo_retiro),
            "nota_pago": nota_pago.strip(),
        }
        cfg = _load_config()
        cfg["precios"] = new_p
        cfg["contacto"] = new_c
        cfg["cobro"] = new_cobro
        _save_config(cfg)
        PRECIOS.clear()
        PRECIOS.update(new_p)
        CONTACTO.clear()
        CONTACTO.update(new_c)
        COBRO.clear()
        COBRO.update(new_cobro)
        st.success("Precios, contacto y datos de cobro guardados.")
        st.balloons()
    st.stop()

# ===================== UI INTERACTIVA =====================

import os as _os_brand
_logo = _os_brand.path.join(_os_brand.path.dirname(__file__), "assets", "logo_morisi.png")
_hb1, _hb2, _hb3 = st.columns([1.2, 2, 1])
with _hb1:
    if _os_brand.path.isfile(_logo):
        st.image(_logo, width=200)
    else:
        st.markdown("### MORISI")
with _hb2:
    st.markdown("")
with _hb3:
    st.markdown('<div style="text-align:right;padding-top:18px"><span class="brand-tag">Morisi</span></div>', unsafe_allow_html=True)

st.markdown("## Chapas Perforadas")
st.caption("Diseño a medida · vista previa en vivo · perforación láser")

# Pasos visuales (estilo ciclo de vida)
st.markdown("""
<div class="step-bar">
  <div class="step-pill on"><span class="num" style="background:#ff7814">1</span> Foto</div>
  <div class="step-pill on"><span class="num" style="background:#ff7814">2</span> Medida</div>
  <div class="step-pill on"><span class="num" style="background:#ff7814">3</span> Perforación</div>
  <div class="step-pill on"><span class="num" style="background:#ff7814">4</span> Ajuste</div>
  <div class="step-pill on"><span class="num" style="background:#ff7814">5</span> Polaridad</div>
  <div class="step-pill on"><span class="num" style="background:#ff7814">6</span> Vista previa</div>
  <div class="step-pill on"><span class="num" style="background:#ff7814">7</span> Comprar</div>
</div>
""", unsafe_allow_html=True)

if "foto_bytes" not in st.session_state:
    st.session_state.foto_bytes = None

# ----- Paso 1: subir foto -----
if st.session_state.foto_bytes is None:
    st.markdown('<div class="hero-upload">', unsafe_allow_html=True)
    st.markdown("### ① Subí tu foto")
    st.caption("JPG o PNG · al cargarla se abren todos los controles y la vista previa en vivo")
    up = st.file_uploader("Subir foto", type=["jpg", "jpeg", "png"], label_visibility="collapsed", key="uploader_inicio")
    if up is not None:
        st.session_state.foto_bytes = up.getvalue()
        st.session_state.foto_name = getattr(up, "name", "foto.jpg")
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
    st.info("Subí una imagen para empezar a diseñar de forma interactiva.")
    st.stop()

c_top1, c_top2, c_top3 = st.columns([2, 1, 1])
with c_top3:
    if st.button("↻ Cambiar foto", use_container_width=True):
        st.session_state.foto_bytes = None
        st.rerun()

pil = Image.open(io.BytesIO(st.session_state.foto_bytes))

col_izq, col_der = st.columns([1, 1.25], gap="large")

with col_izq:
    st.markdown('<div class="card-ctrl"><h4>② Medida de chapa</h4></div>', unsafe_allow_html=True)
    medida = st.selectbox("medida", list(MEDIDAS.keys()), label_visibility="collapsed")
    if medida == "Personalizado":
        c1, c2 = st.columns(2)
        with c1:
            base_w = st.number_input("Ancho (mm)", 300, 2400, 1200, 10)
        with c2:
            base_h = st.number_input("Alto (mm)", 300, 2400, 600, 10)
    else:
        base_w, base_h = MEDIDAS[medida]

    es_cuadrada = (base_w == base_h)
    if es_cuadrada:
        unit_w, unit_h = base_w, base_h
        orientacion = "Cuadrada"
    else:
        orientacion = st.radio("Orientación", ["Horizontal", "Vertical"], horizontal=True)
        if orientacion == "Horizontal":
            unit_w, unit_h = max(base_w, base_h), min(base_w, base_h)
        else:
            unit_w, unit_h = min(base_w, base_h), max(base_w, base_h)

    pc1, pc2 = st.columns(2)
    with pc1:
        n_ancho = st.number_input("Paneles ancho", 1, 6, 1, 1)
    with pc2:
        n_alto = st.number_input("Paneles alto", 1, 6, 1, 1)
    ancho_mm = unit_w * int(n_ancho)
    alto_mm = unit_h * int(n_alto)
    st.caption(f"Total **{ancho_mm/1000:.2f} × {alto_mm/1000:.2f} m** · margen 15 mm".replace(".", ","))

    st.markdown('<div class="card-ctrl"><h4>③ Tipo de perforación</h4></div>', unsafe_allow_html=True)
    forma = st.selectbox(
        "forma",
        ["circulos", "cuadrados", "triangulos", "mixto", "calado"],
        format_func=lambda x: {
            "circulos": "● Círculos",
            "cuadrados": "■ Cuadrados",
            "triangulos": "▲ Triángulos",
            "mixto": "◆ Mixto",
            "calado": "▣ Calado",
        }[x],
        label_visibility="collapsed",
    )

    st.markdown('<div class="card-ctrl"><h4>④ Zoom de la foto</h4></div>', unsafe_allow_html=True)
    zoom = st.slider("zoom", 0.7, 2.0, 1.0, 0.05, label_visibility="collapsed")
    st.caption(f"**{zoom:.2f}×** · 1,00 = llena la chapa · más = acerca")

    st.markdown('<div class="card-ctrl"><h4>⑤ Polaridad y filtro</h4></div>', unsafe_allow_html=True)
    polaridad = st.radio(
        "polaridad",
        ["positivo", "negativo"],
        horizontal=True,
        label_visibility="collapsed",
        format_func=lambda x: "○ Positivo" if x == "positivo" else "● Negativo",
    )
    invert = polaridad == "negativo"
    filtro = st.selectbox(
        "filtro",
        ["normal", "contraste", "suave", "contorno", "relieve", "nitidez", "punch", "pixel", "trama"],
        format_func=lambda x: {
            "normal": "Normal", "contraste": "Alto contraste", "suave": "Suave",
            "contorno": "Contorno", "relieve": "Relieve", "nitidez": "Nitidez",
            "punch": "Punch", "pixel": "Pixel", "trama": "Trama densa",
        }[x],
        label_visibility="collapsed",
    )

    st.markdown('<div class="card-ctrl"><h4>Detalle de la imagen</h4></div>', unsafe_allow_html=True)
    nivel = st.slider("detalle", 1, 10, 7, label_visibility="collapsed")
    dmin_p, dmax_p, _, _ = detalle_a_params(nivel)
    st.caption(f"Nivel **{nivel}/10** · agujeros ~{dmin_p:.0f}–{dmax_p:.0f} mm")

    st.markdown('<div class="card-ctrl"><h4>Acabado de compra</h4></div>', unsafe_allow_html=True)
    color = st.radio(
        "color",
        ["Negro", "Gris", "Blanco", "Oro", "Plata", "Frío"],
        horizontal=True,
        label_visibility="collapsed",
    )

    despacho, km, zona = "retiro", 0.0, "CABA"

with col_der:
    st.markdown("#### ⑥ Vista previa en vivo")
    st.caption("Se actualiza al tocar cada control · chapa blanca · perforaciones negras")

    with st.spinner("Actualizando…"):
        holes, dmin, dmax, calado_info = generate_holes(
            pil, ancho_mm, alto_mm,
            forma=forma, nivel=nivel, invert=invert, filtro=filtro, zoom=zoom,
        )
        preview = render_preview(
            holes, ancho_mm, alto_mm,
            color_name=color, calado_info=calado_info, tecnico=True,
        )
        cotiz = precio_final(
            holes, ancho_mm, alto_mm, despacho, km, zona, calado_info=calado_info
        )
        if calado_info and calado_info.get("calado"):
            cotiz["agujeros"] = int(calado_info["mask"].sum())
            modo_txt = "calado"
        else:
            modo_txt = f"{cotiz['agujeros']} perforaciones"

    st.markdown('<div class="preview-frame">', unsafe_allow_html=True)
    st.image(preview, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    tot_m = f"{ancho_mm/1000:.2f} × {alto_mm/1000:.2f} m".replace(".", ",")
    st.markdown(f"**{tot_m}** · {modo_txt}")
    st.caption(f"{polaridad} · {filtro} · zoom {zoom:.2f}× · detalle {nivel}/10 · {color}")

    st.markdown("#### ⑦ Precio y compra")
    st.markdown(
        f'<div class="price-box"><div class="label">Precio final</div>'
        f'<div class="amount">$ {cotiz["total"]:,.0f}</div>'
        f'</div>'.replace(",", "."),
        unsafe_allow_html=True,
    )

    if "checkout" not in st.session_state:
        st.session_state.checkout = False
    if "pedido_ok" not in st.session_state:
        st.session_state.pedido_ok = False

    if st.button("Comprar ahora", type="primary", use_container_width=True):
        st.session_state.checkout = True
        st.session_state.pedido_ok = False
        st.session_state["_cotiz"] = cotiz
        st.session_state["_med"] = (ancho_mm, alto_mm)
        st.session_state["_opts"] = {
            "forma": forma, "polaridad": polaridad, "filtro": filtro,
            "zoom": zoom, "nivel": nivel, "color": color, "modo_txt": modo_txt,
        }
        st.session_state["_holes"] = holes
        st.session_state["_calado"] = calado_info
        st.rerun()

# ---------- Solapa de datos del cliente ----------
if st.session_state.get("checkout"):
    st.markdown("---")
    st.markdown("## Datos de compra")
    st.caption("Completá tus datos para confirmar el pedido · te contactamos por WhatsApp")

    cotiz = st.session_state.get("_cotiz") or {}
    ancho_mm, alto_mm = st.session_state.get("_med", (1200, 1200))
    opts = st.session_state.get("_opts") or {}
    holes = st.session_state.get("_holes") or []

    tot_txt = f"{ancho_mm/1000:.2f} × {alto_mm/1000:.2f} m".replace(".", ",")
    st.info(
        f"Pedido: **{tot_txt}** · {opts.get('modo_txt','')} · {opts.get('color','')} · "
        f"**$ {cotiz.get('total', 0):,.0f}**".replace(",", ".")
    )

    cA, cB = st.columns(2)
    with cA:
        nombre = st.text_input("Nombre y apellido *")
        telefono = st.text_input("WhatsApp / teléfono *", placeholder="Ej: 11 5555-1234")
        email_cli = st.text_input("Email *")
    with cB:
        direccion = st.text_input("Dirección de entrega")
        ciudad = st.text_input("Ciudad / localidad")
        notas = st.text_area("Notas (opcional)", height=80)

    st.markdown("### Forma de pago")
    _metodos = []
    if COBRO.get("acepta_transferencia", True):
        _metodos.append("Transferencia bancaria")
    if COBRO.get("acepta_mercado_pago", True):
        _metodos.append("Mercado Pago (tarjeta / débito)")
    if COBRO.get("acepta_efectivo_retiro", True):
        _metodos.append("Efectivo al retirar")
    if not _metodos:
        _metodos = ["Transferencia bancaria"]
    metodo_pago = st.radio("Método", _metodos, horizontal=True, label_visibility="collapsed")

    if metodo_pago == "Transferencia bancaria":
        st.markdown(
            f"""
<div class="card-ctrl">
<h4>Datos para transferir</h4>
<p style="margin:4px 0;color:#fff8f2"><b>Banco:</b> {COBRO.get('banco') or '—'} &nbsp;·&nbsp; <b>Titular:</b> {COBRO.get('titular') or '—'}</p>
<p style="margin:4px 0;color:#fff8f2"><b>CBU:</b> {COBRO.get('cbu') or '—'} &nbsp;·&nbsp; <b>Alias:</b> {COBRO.get('alias') or '—'}</p>
<p style="margin:4px 0;color:#fff8f2"><b>CUIT:</b> {COBRO.get('cuit') or '—'}</p>
<p style="margin:8px 0 0 0;color:#e8b896;font-size:0.85rem">{COBRO.get('nota_pago','')}</p>
</div>
""",
            unsafe_allow_html=True,
        )
        st.caption("Transferí el monto exacto e indicá el Nº de pedido en el concepto. Enviá el comprobante por WhatsApp.")
    elif metodo_pago.startswith("Mercado Pago"):
        mp = (COBRO.get("mercado_pago_link") or "").strip()
        st.info("Pagas con **tarjeta o débito en Mercado Pago**. No cargues los datos de la tarjeta acá: se hace en el sitio seguro de Mercado Pago.")
        if mp:
            st.markdown(f"[💳 Ir a pagar en Mercado Pago]({mp})")
        else:
            st.warning("El taller aún no cargó el link de Mercado Pago. Podés pagar por transferencia o coordinar por WhatsApp.")
        st.caption(str(COBRO.get("nota_pago", "")))
    else:
        st.info("Pagás en efectivo al retirar la chapa en el taller.")
        st.caption(str(COBRO.get("nota_pago", "")))

    colx1, colx2 = st.columns(2)
    with colx1:
        if st.button("← Volver al diseño"):
            st.session_state.checkout = False
            st.session_state.pedido_ok = False
            st.rerun()
    with colx2:
        confirmar = st.button("Confirmar pedido", type="primary", use_container_width=True)

    if confirmar:
        if not nombre.strip() or not telefono.strip() or not email_cli.strip():
            st.error("Completá nombre, teléfono y email.")
        else:
            import datetime as _dt
            import urllib.parse as _up
            pedido_id = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
            pedidos_dir = _os.path.join(_os.path.dirname(__file__), "pedidos")
            _os.makedirs(pedidos_dir, exist_ok=True)

            # DXF simple (círculos / contorno)
            def _write_dxf(path, holes, w, h):
                lines = []
                def add(s): lines.append(s)
                add("0"); add("SECTION"); add("2"); add("HEADER")
                add("9"); add("$ACADVER"); add("1"); add("AC1009")
                add("9"); add("$INSUNITS"); add("70"); add("4")
                add("0"); add("ENDSEC")
                add("0"); add("SECTION"); add("2"); add("TABLES")
                add("0"); add("TABLE"); add("2"); add("LTYPE"); add("70"); add("2")
                add("0"); add("LTYPE"); add("2"); add("CONTINUOUS"); add("70"); add("0")
                add("3"); add("Solid"); add("72"); add("65"); add("73"); add("0"); add("40"); add("0.0")
                add("0"); add("LTYPE"); add("2"); add("DASHED"); add("70"); add("0")
                add("3"); add("Dashed"); add("72"); add("65"); add("73"); add("2"); add("40"); add("7.5")
                add("49"); add("5.0"); add("49"); add("-2.5")
                add("0"); add("ENDTAB")
                add("0"); add("TABLE"); add("2"); add("LAYER"); add("70"); add("3")
                add("0"); add("LAYER"); add("2"); add("0"); add("70"); add("0"); add("62"); add("7"); add("6"); add("CONTINUOUS")
                add("0"); add("LAYER"); add("2"); add("PERFORACIONES"); add("70"); add("0"); add("62"); add("7"); add("6"); add("CONTINUOUS")
                add("0"); add("LAYER"); add("2"); add("CONTORNO"); add("70"); add("0"); add("62"); add("2"); add("6"); add("DASHED")
                add("0"); add("ENDTAB"); add("0"); add("ENDSEC")
                add("0"); add("SECTION"); add("2"); add("ENTITIES")
                for (x1, y1), (x2, y2) in [((0, 0), (w, 0)), ((w, 0), (w, h)), ((w, h), (0, h)), ((0, h), (0, 0))]:
                    add("0"); add("LINE"); add("8"); add("CONTORNO"); add("6"); add("DASHED"); add("62"); add("2")
                    add("10"); add(f"{x1:.3f}"); add("20"); add(f"{y1:.3f}"); add("30"); add("0.0")
                    add("11"); add(f"{x2:.3f}"); add("21"); add(f"{y2:.3f}"); add("31"); add("0.0")
                for hitem in holes:
                    if len(hitem) >= 3:
                        cx, cy, size = hitem[0], hitem[1], hitem[2]
                        shape = hitem[3] if len(hitem) > 3 else "circle"
                        if shape == "circle" or shape not in ("square", "triangle"):
                            add("0"); add("CIRCLE"); add("8"); add("PERFORACIONES")
                            add("10"); add(f"{cx:.3f}"); add("20"); add(f"{cy:.3f}"); add("30"); add("0.0")
                            add("40"); add(f"{size/2:.3f}")
                        elif shape == "square":
                            half = size / 2
                            pts = [(cx-half, cy-half), (cx+half, cy-half), (cx+half, cy+half), (cx-half, cy+half), (cx-half, cy-half)]
                            for i in range(4):
                                add("0"); add("LINE"); add("8"); add("PERFORACIONES")
                                add("10"); add(f"{pts[i][0]:.3f}"); add("20"); add(f"{pts[i][1]:.3f}"); add("30"); add("0.0")
                                add("11"); add(f"{pts[i+1][0]:.3f}"); add("21"); add(f"{pts[i+1][1]:.3f}"); add("31"); add("0.0")
                        else:
                            import math as _m
                            r = size / 2
                            pts = []
                            for k in range(3):
                                ang = -_m.pi/2 + k * 2*_m.pi/3
                                pts.append((cx + r*_m.cos(ang), cy + r*_m.sin(ang)))
                            pts.append(pts[0])
                            for i in range(3):
                                add("0"); add("LINE"); add("8"); add("PERFORACIONES")
                                add("10"); add(f"{pts[i][0]:.3f}"); add("20"); add(f"{pts[i][1]:.3f}"); add("30"); add("0.0")
                                add("11"); add(f"{pts[i+1][0]:.3f}"); add("21"); add(f"{pts[i+1][1]:.3f}"); add("31"); add("0.0")
                add("0"); add("ENDSEC"); add("0"); add("EOF")
                with open(path, "w", encoding="utf-8") as f:
                    f.write("\n".join(lines) + "\n")

            dxf_name = f"pedido_{pedido_id}.dxf"
            dxf_path = _os.path.join(pedidos_dir, dxf_name)
            try:
                _write_dxf(dxf_path, holes, float(ancho_mm), float(alto_mm))
                with open(dxf_path, "rb") as f:
                    dxf_bytes = f.read()
            except Exception as e:
                dxf_bytes = None
                st.warning(f"No se pudo generar DXF: {e}")

            pedido = {
                "id": pedido_id,
                "cliente": {
                    "nombre": nombre.strip(),
                    "telefono": telefono.strip(),
                    "email": email_cli.strip(),
                    "direccion": direccion.strip(),
                    "ciudad": ciudad.strip(),
                    "notas": notas.strip(),
                },
                "pago": {
                    "metodo": metodo_pago,
                    "estado": "pendiente",
                },
                "producto": {
                    "medida_mm": [ancho_mm, alto_mm],
                    "medida_txt": tot_txt,
                    **opts,
                    "precio_total": cotiz.get("total", 0),
                },
                "taller": {
                    "email": CONTACTO.get("email_taller", ""),
                    "whatsapp": CONTACTO.get("whatsapp_taller", ""),
                },
                "fecha": _dt.datetime.now().isoformat(timespec="seconds"),
            }
            json_path = _os.path.join(pedidos_dir, f"pedido_{pedido_id}.json")
            with open(json_path, "w", encoding="utf-8") as f:
                _json.dump(pedido, f, indent=2, ensure_ascii=False)

            st.session_state.pedido_ok = True
            st.session_state["_pedido"] = pedido
            st.session_state["_dxf_bytes"] = dxf_bytes
            st.session_state["_dxf_name"] = dxf_name
            st.rerun()

    if st.session_state.get("pedido_ok"):
        import urllib.parse as _up
        pedido = st.session_state.get("_pedido") or {}
        st.success("¡Pedido registrado!")
        st.markdown(
            f"**Nº {pedido.get('id','')}** · Total **$ {pedido.get('producto',{}).get('precio_total',0):,.0f}**".replace(",", ".")
        )

        # DXF solo para el taller (no se ofrece descarga al cliente)
        email_t = CONTACTO.get("email_taller", "")
        wa = CONTACTO.get("whatsapp_taller", "")
        cli = pedido.get("cliente", {})
        prod = pedido.get("producto", {})
        msg = (
            f"Hola {CONTACTO.get('nombre_taller','Morisi')}, confirmo mi pedido de chapa perforada.\\n"
            f"Nº: {pedido.get('id')}\\n"
            f"Cliente: {cli.get('nombre')} · {cli.get('telefono')}\\n"
            f"Email: {cli.get('email')}\\n"
            f"Medida: {prod.get('medida_txt')} · {prod.get('modo_txt')} · {prod.get('color')}\\n"
            f"Total: $ {prod.get('precio_total',0):,.0f}\\n"
            f"Dirección: {cli.get('direccion')} · {cli.get('ciudad')}\\n"
            f"Notas: {cli.get('notas')}"
        ).replace(",", ".")
        wa_url = f"https://wa.me/{wa}?text=" + _up.quote(msg) if wa else ""
        mail_subj = _up.quote(f"Pedido Morisi {pedido.get('id')} · DXF + comprobante")
        mail_body = _up.quote(msg.replace("\\n", "\n") + "\n\nAdjuntar el DXF descargado.")
        mail_url = f"mailto:{email_t}?subject={mail_subj}&body={mail_body}" if email_t else ""

        pago = pedido.get("pago", {})
        if pago.get("metodo") == "Transferencia bancaria":
            st.markdown(
                f"**Transferí a:** CBU `{COBRO.get('cbu') or '—'}` · Alias `{COBRO.get('alias') or '—'}` · "
                f"Titular {COBRO.get('titular') or '—'}"
            )
        elif str(pago.get("metodo", "")).startswith("Mercado Pago"):
            mp = (COBRO.get("mercado_pago_link") or "").strip()
            if mp:
                st.markdown(f"[💳 Completar pago en Mercado Pago]({mp})")
        st.markdown("### Confirmar por WhatsApp y avisar al taller")
        if wa_url:
            st.markdown(f"[📲 Abrir WhatsApp con el pedido]({wa_url})")
        if mail_url:
            st.markdown(f"[✉️ Preparar mail al taller ({email_t})]({mail_url})")
            st.caption("El taller recibe el aviso por mail/WhatsApp. El archivo DXF es solo para la empresa (máquina láser).")
        st.caption("Tus datos y el pedido quedaron registrados. El DXF lo usa solo el taller para el corte láser.")

st.caption("Morisi · Chapas Perforadas")
