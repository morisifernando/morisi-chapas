#!/usr/bin/env python3
"""
Motor de cálculo de precios para chapas perforadas.
Los precios unitarios se cargan desde precios_config.json
Incluye despacho por distancia / zonas / retiro en local.
"""

import json
import math
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional


CONFIG_PATH = Path(__file__).parent / "precios_config.json"


def cargar_config(path: str | Path = CONFIG_PATH) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def guardar_config(config: dict, path: str | Path = CONFIG_PATH):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def perimetro_forma(size_mm: float, shape: str) -> float:
    if shape == "circle":
        return math.pi * size_mm
    elif shape == "square":
        return 4.0 * size_mm
    elif shape == "triangle":
        return 3.0 * size_mm
    return math.pi * size_mm


def calcular_metricas(
    holes: List[Tuple],
    design_w_mm: float,
    design_h_mm: float,
    incluir_contorno: bool = True,
) -> dict:
    total_cut_mm = 0.0
    area_agujeros_mm2 = 0.0
    n_circulos = n_cuadrados = n_triangulos = 0

    for h in holes:
        if len(h) == 4:
            x, y, size, shape = h
        else:
            x, y, size = h[0], h[1], h[2]
            shape = "circle"

        peri = perimetro_forma(size, shape)
        total_cut_mm += peri

        if shape == "circle":
            area_agujeros_mm2 += math.pi * (size / 2) ** 2
            n_circulos += 1
        elif shape == "square":
            area_agujeros_mm2 += size * size
            n_cuadrados += 1
        elif shape == "triangle":
            area_agujeros_mm2 += (math.sqrt(3) / 4) * size * size
            n_triangulos += 1

    contorno_mm = 0.0
    if incluir_contorno:
        contorno_mm = 2 * (design_w_mm + design_h_mm)
        total_cut_mm += contorno_mm

    area_pieza_mm2 = design_w_mm * design_h_mm
    area_pieza_m2 = area_pieza_mm2 / 1_000_000

    # Peso aproximado chapa acero 1.2 mm ≈ 9.42 kg/m²
    peso_kg = area_pieza_m2 * 9.42

    return {
        "ancho_mm": design_w_mm,
        "alto_mm": design_h_mm,
        "area_pieza_m2": round(area_pieza_m2, 4),
        "area_agujeros_m2": round(area_agujeros_mm2 / 1_000_000, 4),
        "area_neta_m2": round((area_pieza_mm2 - area_agujeros_mm2) / 1_000_000, 4),
        "perimetro_agujeros_mm": round(total_cut_mm - contorno_mm, 1),
        "perimetro_contorno_mm": round(contorno_mm, 1),
        "perimetro_total_mm": round(total_cut_mm, 1),
        "cantidad_agujeros": len(holes),
        "circulos": n_circulos,
        "cuadrados": n_cuadrados,
        "triangulos": n_triangulos,
        "peso_aprox_kg": round(peso_kg, 2),
    }


def calcular_despacho(
    config: dict,
    metodo: str = "retiro",
    km: float = 0.0,
    zona: Optional[str] = None,
) -> dict:
    """
    Calcula el costo de despacho.
    metodo: "retiro" | "distancia" | "zona"
    km: kilómetros (solo para metodo=distancia)
    zona: nombre de zona (solo para metodo=zona)
    """
    desp = config.get("despacho", {})

    if metodo == "retiro":
        retiro = desp.get("retiro_en_local", {})
        precio = retiro.get("precio", 0) if retiro.get("activo", True) else 0
        return {
            "item": retiro.get("etiqueta", "Retiro en local"),
            "metodo": "retiro",
            "cantidad": 1,
            "unidad": "u",
            "precio_unitario": precio,
            "subtotal": round(precio, 2),
            "detalle": "El cliente retira en el local",
        }

    if metodo == "distancia":
        env = desp.get("envio_por_distancia", {})
        if not env.get("activo", True):
            return {
                "item": "Envío por distancia (no disponible)",
                "metodo": "distancia",
                "cantidad": 0,
                "unidad": "km",
                "precio_unitario": 0,
                "subtotal": 0,
                "detalle": None,
            }
        base = env.get("precio_base", 0)
        por_km = env.get("precio_por_km", 0)
        km_min = env.get("km_minimos", 0)
        km_cobrados = max(km, km_min)
        subtotal = base + (km_cobrados * por_km)
        return {
            "item": "Envío por distancia",
            "metodo": "distancia",
            "cantidad": round(km_cobrados, 1),
            "unidad": "km",
            "precio_unitario": por_km,
            "subtotal": round(subtotal, 2),
            "detalle": f"Base ${base:.0f} + {km_cobrados:.1f} km × ${por_km:.0f}/km",
        }

    if metodo == "zona":
        zonas = desp.get("zonas", [])
        zona_sel = None
        for z in zonas:
            if z.get("nombre", "").lower() == (zona or "").lower() and z.get("activo", True):
                zona_sel = z
                break
        if not zona_sel:
            return {
                "item": f"Zona '{zona}' no encontrada",
                "metodo": "zona",
                "cantidad": 0,
                "unidad": "zona",
                "precio_unitario": 0,
                "subtotal": 0,
                "detalle": None,
            }
        precio = zona_sel.get("precio_fijo", 0)
        return {
            "item": f"Envío zona {zona_sel['nombre']}",
            "metodo": "zona",
            "cantidad": 1,
            "unidad": "zona",
            "precio_unitario": precio,
            "subtotal": round(precio, 2),
            "detalle": None,
        }

    return {
        "item": "Despacho",
        "metodo": metodo,
        "cantidad": 0,
        "unidad": "-",
        "precio_unitario": 0,
        "subtotal": 0,
        "detalle": "Método no reconocido",
    }


def calcular_precio(
    metricas: dict,
    config: dict | None = None,
    metros_plegado: float = 0.0,
    despacho_metodo: str = "retiro",
    despacho_km: float = 0.0,
    despacho_zona: Optional[str] = None,
) -> dict:
    """
    Calcula el desglose de precios.
    despacho_metodo: "retiro" | "distancia" | "zona"
    """
    if config is None:
        config = cargar_config()

    desglose = []
    costo_total = 0.0

    # 1. Material
    mat = config["material"]
    cant_mat = metricas["area_pieza_m2"]
    sub_mat = cant_mat * mat["precio_por_m2"]
    desglose.append({
        "item": mat["nombre"],
        "cantidad": round(cant_mat, 4),
        "unidad": "m²",
        "precio_unitario": mat["precio_por_m2"],
        "subtotal": round(sub_mat, 2),
    })
    costo_total += sub_mat

    # 2. Corte láser
    corte = config["corte_laser"]
    velocidad = corte.get("velocidad_mm_por_segundo", 20) or 20
    tiempo_seg = metricas["perimetro_total_mm"] / velocidad
    tiempo_min = tiempo_seg / 60.0
    sub_corte = tiempo_min * corte["precio_por_minuto"]
    desglose.append({
        "item": corte["nombre"],
        "cantidad": round(tiempo_min, 2),
        "unidad": "min",
        "precio_unitario": corte["precio_por_minuto"],
        "subtotal": round(sub_corte, 2),
        "detalle": f"Perímetro total: {metricas['perimetro_total_mm']:.0f} mm @ {velocidad} mm/s",
    })
    costo_total += sub_corte

    # 3. Pintura
    pint = config["pintura"]
    caras = pint.get("caras", 1)
    cant_pint = metricas["area_pieza_m2"] * caras
    sub_pint = cant_pint * pint["precio_por_m2"]
    desglose.append({
        "item": pint["nombre"],
        "cantidad": round(cant_pint, 4),
        "unidad": "m²",
        "precio_unitario": pint["precio_por_m2"],
        "subtotal": round(sub_pint, 2),
        "detalle": f"{caras} cara(s)",
    })
    costo_total += sub_pint

    # 4. Plegado
    pleg = config["plegado"]
    sub_pleg_ml = metros_plegado * pleg.get("precio_por_metro_lineal", 0)
    sub_pleg_fijo = pleg.get("precio_fijo_por_pieza", 0)
    sub_pleg = sub_pleg_ml + sub_pleg_fijo
    if sub_pleg > 0 or metros_plegado > 0:
        desglose.append({
            "item": pleg["nombre"],
            "cantidad": round(metros_plegado, 2),
            "unidad": "m lineales",
            "precio_unitario": pleg.get("precio_por_metro_lineal", 0),
            "subtotal": round(sub_pleg, 2),
            "detalle": f"Fijo: ${sub_pleg_fijo:.2f}" if sub_pleg_fijo else None,
        })
        costo_total += sub_pleg

    # 5. Embalaje
    emb = config["embalaje"]
    sub_emb_m2 = metricas["area_pieza_m2"] * emb.get("precio_por_m2", 0)
    sub_emb_fijo = emb.get("precio_fijo_por_unidad", 0)
    sub_emb = sub_emb_m2 + sub_emb_fijo
    desglose.append({
        "item": emb["nombre"],
        "cantidad": round(metricas["area_pieza_m2"], 4),
        "unidad": "m²",
        "precio_unitario": emb.get("precio_por_m2", 0),
        "subtotal": round(sub_emb, 2),
        "detalle": f"Fijo: ${sub_emb_fijo:.2f}" if sub_emb_fijo else None,
    })
    costo_total += sub_emb

    # 6. Setup
    setup = config["setup"]
    sub_setup = setup.get("precio_fijo", 0)
    desglose.append({
        "item": setup["nombre"],
        "cantidad": 1,
        "unidad": "pedido",
        "precio_unitario": sub_setup,
        "subtotal": round(sub_setup, 2),
    })
    costo_total += sub_setup

    # 7. Otros
    for otro in config.get("otros", []):
        cant = otro.get("cantidad", 1)
        pu = otro.get("precio_unitario", 0)
        sub = cant * pu
        desglose.append({
            "item": otro.get("nombre", "Otro"),
            "cantidad": cant,
            "unidad": otro.get("unidad", "u"),
            "precio_unitario": pu,
            "subtotal": round(sub, 2),
        })
        costo_total += sub

    # 8. Margen (sobre costo de producción, sin despacho)
    margen_pct = config.get("margen", {}).get("porcentaje", 0)
    monto_margen = costo_total * (margen_pct / 100.0)
    subtotal_con_margen = costo_total + monto_margen

    # 9. Despacho
    item_despacho = calcular_despacho(
        config,
        metodo=despacho_metodo,
        km=despacho_km,
        zona=despacho_zona,
    )
    desglose.append(item_despacho)
    precio_final = subtotal_con_margen + item_despacho["subtotal"]

    return {
        "desglose": desglose,
        "costo_produccion": round(costo_total, 2),
        "margen_porcentaje": margen_pct,
        "margen_monto": round(monto_margen, 2),
        "subtotal_con_margen": round(subtotal_con_margen, 2),
        "despacho": item_despacho,
        "precio_final": round(precio_final, 2),
        "metricas": metricas,
    }


def imprimir_cotizacion(resultado: dict):
    m = resultado["metricas"]
    print("\n" + "=" * 58)
    print("           COTIZACIÓN DE CHAPA PERFORADA")
    print("=" * 58)
    print(f"  Dimensiones     : {m['ancho_mm']:.0f} × {m['alto_mm']:.0f} mm")
    print(f"  Área pieza      : {m['area_pieza_m2']:.4f} m²")
    print(f"  Peso aprox.     : {m.get('peso_aprox_kg', 0):.2f} kg")
    print(f"  Agujeros        : {m['cantidad_agujeros']}  "
          f"(○{m['circulos']}  □{m['cuadrados']}  △{m['triangulos']})")
    print(f"  Perímetro total : {m['perimetro_total_mm']:.0f} mm")
    print("-" * 58)
    print(f"  {'Ítem':<34} {'Cant.':>7} {'P.Unit':>8} {'Subtotal':>9}")
    print("-" * 58)
    for d in resultado["desglose"]:
        print(f"  {d['item']:<34} {d['cantidad']:>7} {d['precio_unitario']:>8.2f} {d['subtotal']:>9.2f}")
        if d.get("detalle"):
            print(f"    └─ {d['detalle']}")
    print("-" * 58)
    print(f"  {'Costo producción':<34} {'':<7} {'':<8} {resultado['costo_produccion']:>9.2f}")
    if resultado["margen_porcentaje"]:
        print(f"  {'Margen ('+str(resultado['margen_porcentaje'])+'%)':<34} {'':<7} {'':<8} {resultado['margen_monto']:>9.2f}")
        print(f"  {'Subtotal + margen':<34} {'':<7} {'':<8} {resultado['subtotal_con_margen']:>9.2f}")
    print("=" * 58)
    print(f"  {'PRECIO FINAL (con despacho)':<34} {'':<7} {'':<8} {resultado['precio_final']:>9.2f}")
    print("=" * 58 + "\n")


# ---------- Demo ----------
if __name__ == "__main__":
    cfg = cargar_config()
    # Precios de ejemplo
    cfg["material"]["precio_por_m2"] = 8500
    cfg["corte_laser"]["precio_por_minuto"] = 120
    cfg["pintura"]["precio_por_m2"] = 3200
    cfg["pintura"]["caras"] = 1
    cfg["plegado"]["precio_por_metro_lineal"] = 1500
    cfg["plegado"]["precio_fijo_por_pieza"] = 500
    cfg["embalaje"]["precio_por_m2"] = 400
    cfg["embalaje"]["precio_fijo_por_unidad"] = 300
    cfg["setup"]["precio_fijo"] = 1500
    cfg["margen"]["porcentaje"] = 30

    # Despacho de ejemplo
    cfg["despacho"]["retiro_en_local"]["precio"] = 0
    cfg["despacho"]["envio_por_distancia"]["precio_base"] = 2500
    cfg["despacho"]["envio_por_distancia"]["precio_por_km"] = 180
    cfg["despacho"]["envio_por_distancia"]["km_minimos"] = 5
    cfg["despacho"]["zonas"][0]["precio_fijo"] = 3500   # CABA
    cfg["despacho"]["zonas"][1]["precio_fijo"] = 5500   # GBA
    cfg["despacho"]["zonas"][2]["precio_fijo"] = 12000  # Interior

    import random
    random.seed(42)
    holes_demo = []
    for _ in range(200):
        size = random.uniform(3, 10)
        shape = random.choice(["circle", "square", "triangle"])
        holes_demo.append((0, 0, size, shape))

    metricas = calcular_metricas(holes_demo, design_w_mm=480, design_h_mm=500)
    metros_plegado = 2 * (0.480 + 0.500)

    print(">>> Ejemplo 1: Retiro en local")
    r1 = calcular_precio(metricas, cfg, metros_plegado=metros_plegado, despacho_metodo="retiro")
    imprimir_cotizacion(r1)

    print(">>> Ejemplo 2: Envío por distancia (25 km)")
    r2 = calcular_precio(metricas, cfg, metros_plegado=metros_plegado,
                         despacho_metodo="distancia", despacho_km=25)
    imprimir_cotizacion(r2)

    print(">>> Ejemplo 3: Envío zona GBA")
    r3 = calcular_precio(metricas, cfg, metros_plegado=metros_plegado,
                         despacho_metodo="zona", despacho_zona="GBA")
    imprimir_cotizacion(r3)

    print("NOTA: Precios de ejemplo. Editá precios_config.json con tus valores.")
    print(f"Ruta: {CONFIG_PATH}")
