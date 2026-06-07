#!/usr/bin/env python3
"""Extrae las capturas (imágenes JPEG embebidas) de un PDF de entrega a ficheros sueltos.

Las capturas de Dataiku se incrustan como JPEG (DCTDecode). El texto que extraemos del
PDF NO incluye estas imágenes, así que para verificar que el alumno adjuntó lo que pide el
enunciado hay que sacarlas a disco y MIRARLAS (herramienta Read) una a una.

Uso:
    python3 extraer-capturas.py <pdf> [carpeta_salida]

Salida por stdout: "CAPTURAS_EXTRAIDAS: N" y la ruta de cada fichero, para que el agente
pueda abrirlas con Read y juzgar si son coherentes con las secciones del enunciado.
Solo trabaja con la stdlib (re/os): no necesita pip, pdfplumber ni librerías de imagen.
"""
import os
import re
import sys


def extraer(pdf_path, outdir):
    os.makedirs(outdir, exist_ok=True)
    data = open(pdf_path, "rb").read()
    rutas = []
    # Recortar cada JPEG: desde un SOI (FF D8 FF) hasta el último EOI (FF D9) de su bloque.
    for parte in data.split(b"\xff\xd8\xff")[1:]:
        fin = parte.rfind(b"\xff\xd9")
        if fin == -1:
            continue
        jpg = b"\xff\xd8\xff" + parte[: fin + 2]
        if len(jpg) < 200:  # descartar restos minúsculos que no son capturas reales
            continue
        ruta = os.path.join(outdir, f"cap_{len(rutas) + 1:02d}.jpg")
        open(ruta, "wb").write(jpg)
        rutas.append(ruta)
    return rutas


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("uso: python3 extraer-capturas.py <pdf> [carpeta_salida]", file=sys.stderr)
        sys.exit(2)
    pdf = sys.argv[1]
    outdir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(pdf) or ".", "caps")
    rutas = extraer(pdf, outdir)
    print(f"CAPTURAS_EXTRAIDAS: {len(rutas)}")
    for r in rutas:
        print(r)
