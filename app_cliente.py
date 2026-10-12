#!/usr/bin/env python3
"""Chapas Perforadas Cordini – UI limpia. Cliente solo ve precio final."""

import io, math, random
import numpy as np
import streamlit as st
from PIL import Image, ImageDraw, ImageOps, ImageFilter, ImageEnhance

PRECIOS = {
    "material_m2": 8500, "corte_por_minuto": 120, "velocidad_mm_s": 20,
    "pintura_m2": 3200, "pintura_caras": 1, "plegado_ml": 1500, "plegado_fijo": 500,
    "embalaje_m2": 400, "embalaje_fijo": 300, "setup": 1500, "margen_pct": 30,
    "despacho_base": 2500, "despacho_por_km": 180, "despacho_km_min": 5,
    "zonas": {"CABA": 3500, "GBA": 5500, "Interior": 12000},
}
MEDIDAS = {
    "30 × 40 cm": (300, 400), "40 × 50 cm": (400, 500),
    "50 × 60 cm": (500, 600), "60 × 80 cm": (600, 800), "Personalizado": None,
}

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', system-ui, sans-serif; }
.stApp { background: #f8f8f6; }
h1, h2, h3 { color: #1c1c1c !important; font-weight: 600 !important; }
.stButton > button[kind="primary"] {
    background: #1c1c1c !important; color: #fff !important; border: none !important;
    border-radius: 8px !important; font-weight: 600 !important; padding: 0.7rem 1.4rem !important;
}
.stButton > button[kind="primary"]:hover { background: #333 !important; }
div[data-testid="stMetric"] {
    background: #fff; border-radius: 10px; padding: 12px; border: 1px solid #e0e0de;
}
.price-only {
    background: #fff; border: 1px solid #e0e0de; border-radius: 12px;
    padding: 1.5rem 1.6rem; margin-top: 0.5rem;
}
.price-only .label { font-size: 0.85rem; color: #787876; margin-bottom: 0.3rem; }
.price-only .amount { font-size: 2.4rem; font-weight: 700; color: #1c1c1c; }
.price-only .note { font-size: 0.85rem; color: #787876; margin-top: 0.6rem; }
header { visibility: hidden; }
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


def enhance_image(pil_img):
    img = pil_img.convert("L")
    img = ImageOps.autocontrast(img, cutoff=1)
    img = ImageEnhance.Contrast(img).enhance(1.35)
    img = img.filter(ImageFilter.UnsharpMask(radius=1.2, percent=120, threshold=2))
    return img


def analyze(img):
    pixels = img.flatten().astype(float) / 255.0
    mean_b, p50 = float(np.mean(pixels)), float(np.percentile(pixels, 50))
    p90, p10 = float(np.percentile(pixels, 90)), float(np.percentile(pixels, 10))
    contrast = p90 - p10
    if mean_b > 0.75: threshold = min(0.92, p50 + 0.25)
    elif mean_b < 0.35: threshold = max(0.40, p50 + 0.15)
    else: threshold = min(0.85, max(0.45, p50 + 0.18))
    if contrast > 0.55: dmin, dmax = 3.5, 11.0
    elif contrast < 0.30: dmin, dmax = 4.0, 8.5
    else: dmin, dmax = 3.5, 10.0
    sep = 2.8 if contrast > 0.45 else 3.5
    return threshold, dmin, dmax, sep


def generate_holes(pil_img, design_w, design_h, forma="circulos", seed=42):
    img_enh = enhance_image(pil_img)
    px_per_mm = 4.0
    arr = np.array(img_enh.resize(
        (max(40, int(design_w * px_per_mm)), max(40, int(design_h * px_per_mm))),
        Image.Resampling.LANCZOS))
    threshold, dmin, dmax, sep = analyze(arr)
    random.seed(seed)
    holes, failed = [], 0
    allowed = {"circulos": ["circle"], "cuadrados": ["square"], "triangulos": ["triangle"],
               "mixto": ["circle", "square", "triangle"]}.get(forma, ["circle"])

    def brightness(x, y):
        px, py = int(x * px_per_mm), int(y * px_per_mm)
        h, w = arr.shape
        if px < 0 or px >= w or py < 0 or py >= h: return 1.0
        r = 3
        return float(np.mean(arr[max(0, py-r):min(h, py+r+1), max(0, px-r):min(w, px+r+1)])) / 255.0

    def overlaps(a, b, s):
        return math.hypot(a[0]-b[0], a[1]-b[1]) < (a[2]+b[2]+s)

    while failed < 14000 and len(holes) < 4000:
        if random.random() < 0.7:
            x = max(0, min(design_w, random.gauss(design_w/2, design_w/3.2)))
            y = max(0, min(design_h, random.gauss(design_h/2, design_h/3.2)))
        else:
            x, y = random.uniform(0, design_w), random.uniform(0, design_h)
        b = brightness(x, y)
        if b >= threshold:
            failed += 1; continue
        t = max(0.0, min(1.0, b / threshold))
        size = max(dmin, min(dmax, (dmax - t * (dmax - dmin)) * random.uniform(0.88, 1.12)))
        radius = size / 2.0
        if x - radius < 0 or x + radius > design_w or y - radius < 0 or y + radius > design_h:
            failed += 1; continue
        cand = (x, y, radius)
        if any(overlaps(cand, (h[0], h[1], h[2]/2), sep) for h in holes):
            failed += 1; continue
        holes.append((x, y, size, random.choice(allowed)))
        failed = 0
    return holes


def render_preview(holes, design_w, design_h, color_name="Negro", scale=2.8):
    color_map = {
        "Blanco": ((245, 245, 242), (55, 55, 58)),
        "Negro": ((45, 45, 48), (220, 220, 218)),
        "Gris": ((160, 165, 162), (40, 42, 40)),
    }
    bg, fg = color_map.get(color_name, color_map["Negro"])
    # Si negro: fondo claro agujeros oscuros (más legible en pantalla)
    if color_name == "Negro":
        bg, fg = (242, 242, 240), (30, 30, 32)
    w, h = int(design_w * scale), int(design_h * scale)
    img = Image.new("RGB", (w, h), bg)
    draw = ImageDraw.Draw(img)
    for x, y, size, shape in holes:
        s, cx, cy, half = size * scale, x * scale, y * scale, size * scale / 2
        if shape == "circle":
            draw.ellipse([cx-half, cy-half, cx+half, cy+half], fill=fg)
        elif shape == "square":
            draw.rectangle([cx-half, cy-half, cx+half, cy+half], fill=fg)
        else:
            draw.polygon([(cx, cy-half), (cx-half, cy+half*0.8), (cx+half, cy+half*0.8)], fill=fg)
    return img


def precio_final(holes, design_w, design_h, despacho_metodo="retiro", km=0, zona="CABA"):
    total_cut = 2 * (design_w + design_h)
    area_m2 = (design_w * design_h) / 1_000_000
    for _, _, size, shape in holes:
        if shape == "circle": total_cut += math.pi * size
        elif shape == "square": total_cut += 4 * size
        else: total_cut += 3 * size
    tiempo_min = (total_cut / PRECIOS["velocidad_mm_s"]) / 60
    metros_plegado = 2 * ((design_w + design_h) / 1000)
    costo = (area_m2 * PRECIOS["material_m2"]
             + tiempo_min * PRECIOS["corte_por_minuto"]
             + area_m2 * PRECIOS["pintura_caras"] * PRECIOS["pintura_m2"]
             + metros_plegado * PRECIOS["plegado_ml"] + PRECIOS["plegado_fijo"]
             + area_m2 * PRECIOS["embalaje_m2"] + PRECIOS["embalaje_fijo"]
             + PRECIOS["setup"])
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


st.set_page_config(page_title="Chapas Perforadas Cordini", page_icon="◼", layout="wide")

st.markdown("## Diseñá tu bandeja")
st.caption("Subí una imagen · Elegí tamaño y estilo · Precio al instante")

col_izq, col_der = st.columns([1, 1.2], gap="large")

with col_izq:
    st.markdown("**Medida**")
    medida = st.selectbox("medida", list(MEDIDAS.keys()), label_visibility="collapsed")
    if medida == "Personalizado":
        c1, c2 = st.columns(2)
        with c1: ancho_mm = st.number_input("Ancho mm", 150, 1900, 450, 10)
        with c2: alto_mm = st.number_input("Alto mm", 150, 900, 500, 10)
    else:
        ancho_mm, alto_mm = MEDIDAS[medida]

    st.markdown("**Perforación**")
    forma = st.selectbox("forma", ["circulos", "cuadrados", "triangulos", "mixto"],
        format_func=lambda x: {"circulos": "Círculos", "cuadrados": "Cuadrados",
                               "triangulos": "Triángulos", "mixto": "Mixto"}[x],
        label_visibility="collapsed")

    st.markdown("**Color**")
    color = st.selectbox("color", ["Blanco", "Negro", "Gris"], label_visibility="collapsed")

    st.markdown("**Imagen**")
    uploaded = st.file_uploader("img", type=["jpg", "jpeg", "png"], label_visibility="collapsed")

    st.markdown("**Entrega**")
    despacho = st.radio("entrega", ["retiro", "distancia", "zona"],
        format_func=lambda x: {"retiro": "Retiro en taller", "distancia": "Envío por km",
                               "zona": "Envío por zona"}[x],
        label_visibility="collapsed")
    km, zona = 0.0, "CABA"
    if despacho == "distancia":
        km = st.slider("Km", 1, 150, 15)
    elif despacho == "zona":
        zona = st.selectbox("Zona", list(PRECIOS["zonas"].keys()))

    generar = st.button("Generar diseño", type="primary", use_container_width=True)

with col_der:
    if generar and uploaded is None:
        st.warning("Subí una imagen para continuar.")
    elif generar and uploaded is not None:
        with st.spinner("Generando…"):
            pil = Image.open(uploaded)
            holes = generate_holes(pil, ancho_mm, alto_mm, forma=forma)
            preview = render_preview(holes, ancho_mm, alto_mm, color_name=color)
            cotiz = precio_final(holes, ancho_mm, alto_mm, despacho, km, zona)

        st.image(preview, use_container_width=True)
        st.caption(f"{ancho_mm} × {alto_mm} mm · {color} · {cotiz['agujeros']} perforaciones")

        m1, m2, m3 = st.columns(3)
        m1.metric("Agujeros", cotiz["agujeros"])
        m2.metric("Área", f"{cotiz['area_m2']} m²")
        m3.metric("Peso", f"{cotiz['peso_kg']} kg")

        # SOLO PRECIO FINAL – sin desglose
        st.markdown(f"""
        <div class="price-only">
            <div class="label">Precio</div>
            <div class="amount">${cotiz['total']:,.0f}</div>
            <div class="note">Incluye material, corte, pintura, plegado y embalaje.</div>
        </div>
        """, unsafe_allow_html=True)

        st.write("")
        st.button("Comprar", type="primary", use_container_width=True)
        st.caption("Al pagar recibís confirmación por WhatsApp.")

        buf = io.BytesIO()
        preview.save(buf, format="PNG")
        st.download_button("Descargar vista previa", buf.getvalue(), "bandeja.png", "image/png")
    else:
        st.info("Completá los datos y tocá **Generar diseño**.")
