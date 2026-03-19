#!/usr/bin/env python3
"""
actualizar_precios.py
─────────────────────
Scrapea los precios de mano de obra de electroinstalador.com
y actualiza el archivo index.html del proyecto.

Uso:
    python scripts/actualizar_precios.py

Corre automáticamente el día 1 de cada mes via GitHub Actions.
"""

import re
import sys
import json
import time
import logging
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# ─── CONFIG ───────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)

BASE_URL = "https://www.electroinstalador.com"
HEADERS  = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-AR,es;q=0.9",
}
DELAY = 2          # segundos entre requests
TIMEOUT = 15       # timeout por request
INDEX_PATH = Path(__file__).parent.parent / "index.html"

# ─── PÁGINAS A SCRAPEAR ───────────────────────────────────────
# Cada entrada tiene: id interno, label, url de la página fuente
PAGINAS = [
    ("tablero",       "Tableros",             "/paginas/p172-pais--cmo--tablero-domiciliario-y-comercial"),
    ("cableado",      "Cableado",             "/paginas/p130-pais--cmo--cableado"),
    ("canalizacion",  "Canalización",         "/paginas/p136-pais--cmo--canalizacion-caneria"),
    ("luminarias",    "Luminarias",           "/paginas/p151-pais--cmo--colocacion-de-luminarias"),
    ("acometida",     "Acometidas",           "/paginas/p127-pais--cmo--acometidas-y-medidores"),
    ("puesta_tierra", "Puesta a tierra",      "/paginas/p169-pais--cmo--puesta-a-tierra"),
    ("mantenimiento", "Mantenimiento",        "/paginas/p160-pais--cmo--mantenimiento"),
    ("cctv",          "CCTV",                 "/paginas/p148-pais--cmo--cctv"),
    ("proyecto",      "Proyecto eléctrico",   "/paginas/p166-pais--cmo--proyecto-electrico"),
]


# ─── SCRAPING ─────────────────────────────────────────────────
def fetch(url: str) -> BeautifulSoup:
    """Descarga una página y devuelve el objeto BeautifulSoup."""
    log.info(f"  GET {url}")
    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    time.sleep(DELAY)
    return BeautifulSoup(r.text, "html.parser")


def extraer_montos(soup: BeautifulSoup) -> list[int]:
    """
    Extrae todos los montos en pesos del HTML.
    Los precios en el sitio aparecen como: $ 41.600  o  $41.600
    Devuelve lista de enteros ordenados de menor a mayor.
    """
    texto = soup.get_text(" ")
    # Busca patrones tipo $ 41.600 o $41.600 o $ 1.133.900
    patron = r"\$\s*([\d]{1,3}(?:\.[\d]{3})+)"
    matches = re.findall(patron, texto)
    montos = []
    for m in matches:
        try:
            valor = int(m.replace(".", ""))
            if 1000 < valor < 50_000_000:   # rango razonable de precios ARS
                montos.append(valor)
        except ValueError:
            pass
    # Deduplicar manteniendo orden de aparición
    vistos = set()
    unicos = []
    for v in montos:
        if v not in vistos:
            vistos.add(v)
            unicos.append(v)
    return unicos


def obtener_fecha_actualizacion(soup: BeautifulSoup) -> str:
    """Intenta leer la fecha de última actualización que publica el sitio."""
    texto = soup.get_text(" ").upper()
    # Busca patrones tipo "ENERO - FEBRERO 2026" o "MARZO 2026"
    meses = ["ENERO","FEBRERO","MARZO","ABRIL","MAYO","JUNIO",
             "JULIO","AGOSTO","SEPTIEMBRE","OCTUBRE","NOVIEMBRE","DICIEMBRE"]
    for mes in meses:
        if mes in texto:
            # Busca el año cercano
            idx = texto.index(mes)
            fragmento = texto[idx:idx+30]
            year_match = re.search(r"20\d{2}", fragmento)
            if year_match:
                return f"{mes.capitalize()} {year_match.group()}"
    return datetime.now().strftime("%B %Y").capitalize()


def scrapear_pagina(cat_id: str, label: str, path: str) -> dict:
    """Scrapea una categoría y devuelve sus montos."""
    url = BASE_URL + path
    try:
        soup = fetch(url)
        montos = extraer_montos(soup)
        fecha  = obtener_fecha_actualizacion(soup)
        log.info(f"    ✓ {label}: {len(montos)} precios encontrados")
        return {"id": cat_id, "label": label, "montos": montos, "fecha": fecha, "url": url}
    except Exception as e:
        log.warning(f"    ✗ {label}: error — {e}")
        return {"id": cat_id, "label": label, "montos": [], "fecha": "?", "url": url}


# ─── ACTUALIZAR INDEX.HTML ────────────────────────────────────
def leer_trabajos_actuales(html: str) -> list[dict]:
    """Extrae el array TRABAJOS del HTML actual como referencia."""
    m = re.search(r"const TRABAJOS\s*=\s*(\[.*?\]);", html, re.DOTALL)
    if not m:
        return []
    try:
        # Limpia comentarios JS antes de parsear
        bloque = re.sub(r"//[^\n]*", "", m.group(1))
        return json.loads(bloque)
    except Exception:
        return []


def actualizar_precios_en_html(html: str, resultados: list[dict]) -> str:
    """
    Estrategia de actualización:
    Para cada categoría, extrae los montos scrapeados (ordenados) y los
    mapea posicionalmente a los precios existentes en TRABAJOS.
    Si hay menos montos que trabajos, deja el precio original.
    Actualiza también el badge de fecha en el header.
    """
    trabajos = leer_trabajos_actuales(html)
    if not trabajos:
        log.warning("No se encontró el array TRABAJOS en el HTML. Abortando actualización de precios.")
        return html

    # Construir mapa: cat_id -> montos scrapeados
    mapa = {r["id"]: r["montos"] for r in resultados}

    # Contadores por categoría (para mapear posicionalmente)
    contadores: dict[str, int] = {}
    cambios = 0

    nuevos_trabajos = []
    for t in trabajos:
        cat = t.get("cat", "")
        precio_orig = t.get("precio", 0)
        montos_cat  = mapa.get(cat, [])

        idx = contadores.get(cat, 0)
        if idx < len(montos_cat):
            precio_nuevo = montos_cat[idx]
            if precio_nuevo != precio_orig:
                log.info(f"    Actualizando '{t['nombre'][:50]}': ${precio_orig:,} → ${precio_nuevo:,}")
                cambios += 1
            t = {**t, "precio": precio_nuevo}
        contadores[cat] = idx + 1
        nuevos_trabajos.append(t)

    log.info(f"  Total cambios de precio: {cambios}")

    # Serializar de vuelta a JS
    def dict_to_js(d):
        parts = []
        for k, v in d.items():
            if isinstance(v, str):
                v_escaped = v.replace("'", "\\'")
                parts.append(f"  {k}: '{v_escaped}'")
            elif isinstance(v, int):
                parts.append(f"  {k}: {v}")
        return "{ " + ", ".join(parts) + " }"

    js_items = []
    for t in nuevos_trabajos:
        comment = f"  // {t.get('cat','')}"
        js_items.append(comment + "\n  " + dict_to_js(t))

    nuevo_trabajos_js = "const TRABAJOS = [\n" + ",\n".join(js_items) + "\n];"

    html_actualizado = re.sub(
        r"const TRABAJOS\s*=\s*\[.*?\];",
        nuevo_trabajos_js,
        html,
        flags=re.DOTALL
    )

    # Actualizar badge de fecha en el header
    fecha_badge = resultados[0]["fecha"] if resultados else datetime.now().strftime("%b %Y")
    html_actualizado = re.sub(
        r"(✓\s*)([\w\-–]+\s+20\d{2})",
        f"\\1{fecha_badge}",
        html_actualizado
    )

    # Inyectar comentario con timestamp de la última actualización
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M UTC")
    html_actualizado = html_actualizado.replace(
        "// PRECIOS VERIFICADOS",
        f"// Última actualización automática: {timestamp}\n// PRECIOS VERIFICADOS"
    )

    return html_actualizado


# ─── MAIN ─────────────────────────────────────────────────────
def main():
    log.info("═" * 50)
    log.info("PresupuestoElec — Actualizador de precios")
    log.info(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")
    log.info("═" * 50)

    # 1. Verificar que existe index.html
    if not INDEX_PATH.exists():
        log.error(f"No se encontró {INDEX_PATH}")
        sys.exit(1)

    html_original = INDEX_PATH.read_text(encoding="utf-8")
    log.info(f"index.html leído ({len(html_original):,} chars)")

    # 2. Scrapear todas las categorías
    log.info("\nScrapeando electroinstalador.com...")
    resultados = []
    for cat_id, label, path in PAGINAS:
        resultado = scrapear_pagina(cat_id, label, path)
        resultados.append(resultado)

    # Resumen
    total_precios = sum(len(r["montos"]) for r in resultados)
    log.info(f"\nTotal precios encontrados: {total_precios}")

    # 3. Actualizar HTML
    log.info("\nActualizando index.html...")
    html_nuevo = actualizar_precios_en_html(html_original, resultados)

    # 4. Guardar
    INDEX_PATH.write_text(html_nuevo, encoding="utf-8")
    log.info(f"\n✓ index.html actualizado correctamente")

    # 5. Guardar log de precios en JSON (útil para debugging)
    log_path = Path(__file__).parent / "ultimo_scraping.json"
    log_data = {
        "timestamp": datetime.now().isoformat(),
        "categorias": [
            {"id": r["id"], "label": r["label"], "fecha": r["fecha"],
             "cantidad_precios": len(r["montos"]), "muestra": r["montos"][:5]}
            for r in resultados
        ]
    }
    log_path.write_text(json.dumps(log_data, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info(f"Log guardado en {log_path}")
    log.info("═" * 50)


if __name__ == "__main__":
    main()
