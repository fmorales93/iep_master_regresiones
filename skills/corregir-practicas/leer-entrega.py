#!/usr/bin/env python3
"""Lee una entrega PDF de alumno: extrae el TEXTO y las CAPTURAS. Solo stdlib.

Por qué este script (no `pdftotext`/`pdfplumber`): este entorno WSL no tiene pip ni
librerías PDF, y los PDFs reales del curso usan formatos que rompen una extracción ingenua:
  - Texto con fuentes subset + CMap ToUnicode (cadenas hexadecimales `<00AB>` en operadores TJ).
  - Content streams a veces SIN comprimir (no FlateDecode) -> hay que tener fallback.
  - Capturas de Dataiku como JPEG (DCTDecode) O como bitmap crudo (FlateDecode, sin predictor):
    DeviceRGB, DeviceGray o ICCBased (hay que resolver /N del perfil: 3=RGB, 1=gris).
Una extracción que solo mire `(texto) Tj` en streams Flate devuelve ruido o vacío. Este lector
maneja los tres casos. Está probado contra entregas reales de las tres prácticas.

Uso:
    python3 leer-entrega.py <pdf> [carpeta_capturas]

Efectos:
  - Escribe `<pdf sin .pdf>.txt` con el texto extraído.
  - Vuelca las capturas a la carpeta indicada (por defecto `<dir del pdf>/caps`).
  - Imprime por stdout: `TEXT_CHARS: N  CMAP: M  IMAGES: K -> carpeta`.

Después: LEE el .txt (interpretación del alumno) y ABRE cada captura con la herramienta Read
para comprobar que se corresponde con lo que pide el enunciado (ver SKILL.md, PASO 1d).
"""
import os
import re
import struct
import sys
import zlib


def _streams(data):
    """Cada stream del PDF, descomprimido si es FlateDecode, o crudo si no."""
    for m in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", data, re.DOTALL):
        raw = m.group(1)
        try:
            yield zlib.decompress(raw)
        except Exception:
            yield raw  # fallback: stream sin comprimir


def build_cmap(data):
    """Mapa código->Unicode a partir de los CMap ToUnicode (bfchar/bfrange)."""
    cmap = {}
    for dec in _streams(data):
        if b"beginbfchar" not in dec and b"beginbfrange" not in dec:
            continue
        t = dec.decode("latin-1", "replace")
        for blk in re.findall(r"beginbfchar(.*?)endbfchar", t, re.DOTALL):
            for src, dst in re.findall(r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", blk):
                try:
                    cmap[int(src, 16)] = bytes.fromhex(dst).decode("utf-16-be", "replace")
                except Exception:
                    pass
        for blk in re.findall(r"beginbfrange(.*?)endbfrange", t, re.DOTALL):
            for lo, hi, dst in re.findall(r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", blk):
                lo_i, hi_i, base = int(lo, 16), int(hi, 16), int(dst, 16)
                for i in range(hi_i - lo_i + 1):
                    cmap[lo_i + i] = chr(base + i)
    return cmap


def extract_text(data, cmap):
    def dh(h):
        h = re.sub(r"\s", "", h)
        out = ""
        for i in range(0, len(h), 4):
            g = h[i:i + 4]
            if len(g) == 4:
                out += cmap.get(int(g, 16), "")
        return out

    out = []
    for dec in _streams(data):
        if dec[:4] in (b"\x00\x01\x00\x00", b"OTTO", b"true", b"ttcf") or b"glyf" in dec[:2000]:
            continue  # saltar ficheros de fuente
        if not re.search(rb"\bTJ\b|\bTj\b", dec):
            continue
        t = dec.decode("latin-1", "replace")
        for tjar in re.findall(r"\[(.*?)\]\s*TJ", t, re.DOTALL):
            line = "".join(dh(h) for h in re.findall(r"<([0-9A-Fa-f\s]+)>", tjar))
            line += "".join(p[1:-1] for p in re.findall(r"\((?:[^()\\]|\\.)*\)", tjar))
            if line.strip():
                out.append(line)
        for h in re.findall(r"<([0-9A-Fa-f\s]+)>\s*Tj", t):
            if dh(h).strip():
                out.append(dh(h))
        for p in re.findall(r"\((?:[^()\\]|\\.)*\)\s*Tj", t):
            s = p[1:p.rfind(")")]
            if s.strip():
                out.append(s)
    txt = "\n".join(out)
    return re.sub(r"\\([()\\])", r"\1", txt)


def _png(w, h, pixels, path, comps=3):
    """Escribe un PNG de 8 bpc. comps=3 -> RGB (color type 2); comps=1 -> gris (type 0)."""
    color_type = 2 if comps == 3 else 0
    stride = w * comps
    rows = bytearray()
    for y in range(h):
        rows.append(0)  # byte de filtro PNG (None) por scanline
        rows += pixels[y * stride:(y + 1) * stride]
    comp = zlib.compress(bytes(rows), 9)

    def ch(typ, d):
        c = typ + d
        return struct.pack(">I", len(d)) + c + struct.pack(">I", zlib.crc32(c) & 0xffffffff)

    open(path, "wb").write(
        b"\x89PNG\r\n\x1a\n"
        + ch(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, color_type, 0, 0, 0))
        + ch(b"IDAT", comp)
        + ch(b"IEND", b"")
    )


def _icc_components(data, objnum):
    """Nº de componentes (/N) del objeto ICCBased `objnum 0 obj`. RGB=3, gris=1, CMYK=4."""
    m = re.search((r"\b%d\s+0\s+obj\b" % objnum).encode(), data)
    if not m:
        return None
    seg = data[m.end():m.end() + 400]
    nm = re.search(rb"/N\s+(\d+)", seg)
    return int(nm.group(1)) if nm else None


def extract_images(data, outdir):
    os.makedirs(outdir, exist_ok=True)
    n = 0
    # 1) JPEG (DCTDecode): recortar de SOI (FF D8 FF) al último EOI (FF D9) del bloque.
    for parte in data.split(b"\xff\xd8\xff")[1:]:
        fin = parte.rfind(b"\xff\xd9")
        if fin == -1:
            continue
        jpg = b"\xff\xd8\xff" + parte[:fin + 2]
        if len(jpg) < 2000:  # descartar restos minúsculos (falsos positivos)
            continue
        n += 1
        open(os.path.join(outdir, f"cap_{n:02d}.jpg"), "wb").write(jpg)
    # 2) Bitmap crudo (FlateDecode, 8 bpc, sin predictor) -> PNG. Cubre DeviceRGB/DeviceGray
    #    e ICCBased (resolviendo /N del perfil: 3=RGB, 1=gris). Dataiku exporta las capturas
    #    como ICCBased N=3, así que sin esto se perderían (IMAGES: 0).
    for m in re.finditer(rb"/Subtype\s*/Image", data):
        start = data.rfind(b"<<", 0, m.start())
        s = data.find(b"stream", m.start())
        dic = data[start:s]  # dict completo hasta `stream` (incluye DecodeParms si lo hay)
        if b"DCTDecode" in dic or b"FlateDecode" not in dic:
            continue
        if not re.search(rb"/BitsPerComponent\s+8", dic):
            continue
        if re.search(rb"/Predictor\s+(\d+)", dic):
            continue  # predictor PNG/TIFF no soportado: mejor saltar que volcar basura

        # nº de componentes según el espacio de color
        if b"DeviceRGB" in dic:
            comps = 3
        elif b"DeviceGray" in dic:
            comps = 1
        else:
            icc = re.search(rb"/ICCBased\s+(\d+)\s+0\s+R", dic)
            comps = _icc_components(data, int(icc.group(1))) if icc else None
        if comps not in (1, 3):
            continue

        def gi(k):
            mm = re.search((r"/%s\s+(\d+)" % k).encode(), dic)
            return int(mm.group(1)) if mm else None

        w, h, ln = gi("Width"), gi("Height"), gi("Length")
        if not (w and h):
            continue
        p = s + 6
        if data[p:p + 2] == b"\r\n":
            p += 2
        elif data[p:p + 1] in (b"\n", b"\r"):
            p += 1
        payload = data[p:p + ln] if ln else data[p:data.find(b"endstream", p)]
        try:
            raw = zlib.decompress(payload)
        except Exception:
            continue
        if len(raw) < w * h * comps:
            continue
        n += 1
        _png(w, h, raw[:w * h * comps], os.path.join(outdir, f"cap_{n:02d}.png"), comps)
    return n


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("uso: python3 leer-entrega.py <pdf> [carpeta_capturas]", file=sys.stderr)
        sys.exit(2)
    pdf = sys.argv[1]
    outdir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(pdf) or ".", "caps")
    data = open(pdf, "rb").read()
    cmap = build_cmap(data)
    txt = extract_text(data, cmap)
    open(os.path.splitext(pdf)[0] + ".txt", "w").write(txt)
    nimg = extract_images(data, outdir)
    print(f"TEXT_CHARS: {len(txt)}  CMAP: {len(cmap)}  IMAGES: {nimg} -> {outdir}")
