import os, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bot"))
import config

class TestParseEnv(unittest.TestCase):
    def test_parsea_claves_ignorando_comentarios_y_vacias(self):
        contenido = (
            "# comentario\n"
            "TELEGRAM_BOT_TOKEN=123:abc\n"
            "\n"
            "TELEGRAM_CHAT_ID=999\n"
            "MOODLE_USER=fulano\n"
        )
        with tempfile.NamedTemporaryFile("w", suffix=".env", delete=False) as f:
            f.write(contenido); ruta = f.name
        try:
            d = config.parse_env(ruta)
        finally:
            os.unlink(ruta)
        self.assertEqual(d["TELEGRAM_BOT_TOKEN"], "123:abc")
        self.assertEqual(d["TELEGRAM_CHAT_ID"], "999")
        self.assertEqual(d["MOODLE_USER"], "fulano")
        self.assertNotIn("# comentario", d)

    def test_load_config_calcula_rutas_y_tipa_chat_id(self):
        contenido = "TELEGRAM_BOT_TOKEN=tok\nTELEGRAM_CHAT_ID=42\n"
        with tempfile.TemporaryDirectory() as proj:
            env = os.path.join(proj, ".env")
            with open(env, "w") as f: f.write(contenido)
            cfg = config.load_config(proj, env)
            self.assertEqual(cfg.token, "tok")
            self.assertEqual(cfg.chat_id, 42)
            self.assertEqual(cfg.propuestas_dir, os.path.join(proj, "propuestas"))

if __name__ == "__main__":
    unittest.main()
