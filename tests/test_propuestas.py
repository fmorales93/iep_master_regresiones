import os, sys, unittest, tempfile, json
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

class TestPersistencia(unittest.TestCase):
    def test_guardar_y_cargar_roundtrip(self):
        p = prop_ok()
        with tempfile.TemporaryDirectory() as d:
            ruta = os.path.join(d, "2026-06-07-p2.json")
            propuestas.guardar(p, ruta)
            self.assertEqual(propuestas.cargar(ruta), p)

    def test_listar_ordena_y_devuelve_pares(self):
        with tempfile.TemporaryDirectory() as d:
            propuestas.guardar(prop_ok(), os.path.join(d, "2026-06-07-p2.json"))
            p1 = prop_ok(); p1["practica"] = 1
            propuestas.guardar(p1, os.path.join(d, "2026-06-07-p1.json"))
            listado = propuestas.listar(d)
            nombres = [os.path.basename(r) for r, _ in listado]
            self.assertEqual(nombres, ["2026-06-07-p1.json", "2026-06-07-p2.json"])
            self.assertEqual(listado[0][1]["practica"], 1)

    def test_listar_dir_inexistente_devuelve_vacio(self):
        self.assertEqual(propuestas.listar("/no/existe/x"), [])

    def test_guardar_sobrescribe_existente(self):
        with tempfile.TemporaryDirectory() as d:
            ruta = os.path.join(d, "2026-06-07-p2.json")
            propuestas.guardar(prop_ok(), ruta)
            p2 = prop_ok(); p2["estado"] = "guardada"
            propuestas.guardar(p2, ruta)
            self.assertEqual(propuestas.cargar(ruta)["estado"], "guardada")
            self.assertFalse(os.path.exists(ruta + ".tmp"))

    def test_listar_ignora_no_json(self):
        with tempfile.TemporaryDirectory() as d:
            propuestas.guardar(prop_ok(), os.path.join(d, "2026-06-07-p2.json"))
            with open(os.path.join(d, "nota.txt"), "w") as f:
                f.write("ruido")
            listado = propuestas.listar(d)
            self.assertEqual([os.path.basename(r) for r, _ in listado], ["2026-06-07-p2.json"])

if __name__ == "__main__":
    unittest.main()
