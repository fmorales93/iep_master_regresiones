import os, json

ESTADOS = {"pendiente", "editando", "aprobada", "guardada", "rechazada"}
RUBRICA = {
    "comprension": {0, 1, 2},
    "aplicacion": {0, 1.5, 3},
    "documentacion": {0, 1, 2},
    "resolucion": {0, 1.5, 3},
}

def total_alumno(alumno):
    return sum(alumno["criterios"][k] for k in RUBRICA)

def validar(prop):
    errores = []
    if prop.get("estado") not in ESTADOS:
        errores.append("estado inválido: %r" % prop.get("estado"))
    for al in prop.get("alumnos", []):
        nombre = al.get("nombre", "?")
        crit = al.get("criterios", {})
        for k, permitidos in RUBRICA.items():
            if crit.get(k) not in permitidos:
                errores.append("%s: criterio %s con valor inválido %r" % (nombre, k, crit.get(k)))
        if abs(al.get("total", -1) - total_alumno(al)) > 1e-9:
            errores.append("%s: total no coincide con la suma de criterios" % nombre)
    return errores

def cargar(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def guardar(prop, path):
    directorio = os.path.dirname(path)
    if directorio:
        os.makedirs(directorio, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(prop, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)  # escritura atómica

def listar(dirpath):
    if not os.path.isdir(dirpath):
        return []
    pares = []
    for nombre in sorted(os.listdir(dirpath)):
        if nombre.endswith(".json"):
            ruta = os.path.join(dirpath, nombre)
            pares.append((ruta, cargar(ruta)))
    return pares

NOMBRES_PRACTICA = {
    1: "Análisis de precios Idealista",
    2: "Boston Housing (OLS + Ridge + Lasso)",
    3: "Detección de fraude (regresión logística)",
}

def escapar_html(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def _fila_ascii(al):
    c = al["criterios"]
    nombre = al["nombre"][:24].ljust(24)
    return "%s  %3s %3s %3s %3s  %4s" % (
        nombre, c["comprension"], c["aplicacion"],
        c["documentacion"], c["resolucion"], al["total"])

def construir_mensajes(prop, limite=4096):
    titulo = "<b>Práctica %s — %s</b>\n%d alumnos · estado: %s" % (
        prop["practica"], NOMBRES_PRACTICA.get(prop["practica"], ""),
        len(prop["alumnos"]), prop["estado"])
    cabecera = "%s  %3s %3s %3s %3s  %4s" % (
        "Alumno".ljust(24), "CT", "AP", "DO", "RP", "Tot")
    filas = [escapar_html(_fila_ascii(al)) for al in prop["alumnos"]]

    mensajes, bloque, primero = [], [], True
    def cerrar(bloque, primero):
        cuerpo = "<pre>" + "\n".join([escapar_html(cabecera)] + bloque) + "</pre>"
        return (titulo + "\n" + cuerpo) if primero else cuerpo

    for fila in filas:
        candidato = cerrar(bloque + [fila], primero)
        if len(candidato) > limite and bloque:
            mensajes.append(cerrar(bloque, primero)); primero = False; bloque = [fila]
        else:
            bloque.append(fila)
    if bloque:
        mensajes.append(cerrar(bloque, primero))
    return mensajes
