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
