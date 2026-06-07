import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bot"))
import propuestas

def alumno_ok():
    return {
        "nombre": "Ana López",
        "grader_url": "https://x/grader&userid=1",
        "criterios": {"comprension": 2, "aplicacion": 1.5, "documentacion": 2, "resolucion": 3},
        "total": 8.5,
        "comentario": "ok",
        "guardado": False,
    }

def prop_ok():
    return {"practica": 2, "fecha": "2026-06-07", "estado": "pendiente",
            "notificado": False, "alumnos": [alumno_ok()]}

class TestValidar(unittest.TestCase):
    def test_propuesta_correcta_sin_errores(self):
        self.assertEqual(propuestas.validar(prop_ok()), [])

    def test_criterio_fuera_de_rango(self):
        p = prop_ok(); p["alumnos"][0]["criterios"]["aplicacion"] = 2  # no permitido
        errores = propuestas.validar(p)
        self.assertTrue(any("aplicacion" in e for e in errores))

    def test_total_incoherente(self):
        p = prop_ok(); p["alumnos"][0]["total"] = 10
        errores = propuestas.validar(p)
        self.assertTrue(any("total" in e.lower() for e in errores))

    def test_estado_invalido(self):
        p = prop_ok(); p["estado"] = "loquesea"
        self.assertTrue(any("estado" in e.lower() for e in propuestas.validar(p)))

if __name__ == "__main__":
    unittest.main()
