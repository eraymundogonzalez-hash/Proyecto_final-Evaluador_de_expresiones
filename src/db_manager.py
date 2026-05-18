# db_manager.py
# Gestión completa de la base de datos SQLite para el sistema de evaluación de expresiones matemáticas.
# Tablas: usuarios, evaluaciones
# Proyecto: Evaluador de Expresiones Matemáticas - Equipo 5

import sqlite3
import hashlib
import json
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path


class DatabaseManager:
    DEFAULT_PATH = Path("evaluaciones.db")

    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path) if db_path else self.DEFAULT_PATH

    def conectar(self) -> sqlite3.Connection:
        """Devuelve una conexión nueva. Úsala siempre con `with`."""
        return sqlite3.connect(self.db_path)

    def inicializar(self) -> None:
        with self.conectar() as conn:
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS usuarios (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    username      TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    creado_en     DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS evaluaciones (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    usuario_id  INTEGER NOT NULL,
                    expresion   TEXT NOT NULL,
                    es_valida   BOOLEAN NOT NULL,
                    resultado   TEXT,
                    error       TEXT,
                    fecha_hora  DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
                )
            """)
            conn.commit()
        print(f"[BD] Base de datos lista en {self.db_path.resolve()}")


class UsuarioRepository:
    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    @staticmethod
    def hash_password(password: str) -> str:
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

    def registrar(self, username: str, password: str) -> tuple[bool, str]:
        if not username.strip() or not password.strip():
            return False, "Usuario y contraseña no pueden estar vacíos."
        try:
            with self.db.conectar() as conn:
                conn.execute(
                    "INSERT INTO usuarios (username, password_hash) VALUES (?, ?)",
                    (username.strip(), self.hash_password(password)),
                )
                conn.commit()
            return True, "Usuario registrado correctamente."
        except sqlite3.IntegrityError:
            return False, f"El usuario '{username}' ya existe."

    def autenticar(self, username: str, password: str) -> tuple[bool, int | None]:
        with self.db.conectar() as conn:
            row = conn.execute(
                "SELECT id, password_hash FROM usuarios WHERE username = ?",
                (username.strip(),),
            ).fetchone()
        if row and row[1] == self.hash_password(password):
            return True, row[0]
        return False, None

    def listar(self) -> list[dict]:
        with self.db.conectar() as conn:
            rows = conn.execute(
                "SELECT id, username, creado_en FROM usuarios ORDER BY id"
            ).fetchall()
        return [{"id": r[0], "username": r[1], "creado_en": r[2]} for r in rows]


class EvaluacionRepository:
    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    def guardar(self, usuario_id: int, resultado: dict) -> int:
        res_texto = str(resultado["resultado"]) if resultado["resultado"] is not None else None
        with self.db.conectar() as conn:
            cur = conn.execute(
                """
                INSERT INTO evaluaciones
                    (usuario_id, expresion, es_valida, resultado, error, fecha_hora)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    usuario_id,
                    resultado["expresion"],
                    resultado["valida"],
                    res_texto,
                    resultado.get("error"),
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                ),
            )
            conn.commit()
        return cur.lastrowid

    def eliminar(self, eval_id: int) -> bool:
        with self.db.conectar() as conn:
            cur = conn.execute(
                "DELETE FROM evaluaciones WHERE id = ?", (eval_id,)
            )
            conn.commit()
        return cur.rowcount > 0

    def consultar_historial(self, usuario_id: int | None = None) -> list[dict]:
        query = """
            SELECT e.id, u.username, e.expresion, e.es_valida,
                   e.resultado, e.error, e.fecha_hora
            FROM evaluaciones e
            JOIN usuarios u ON e.usuario_id = u.id
        """
        params: tuple = ()
        if usuario_id is not None:
            query += " WHERE e.usuario_id = ?"
            params = (usuario_id,)
        query += " ORDER BY e.fecha_hora DESC"
        with self.db.conectar() as conn:
            rows = conn.execute(query, params).fetchall()
        return [
            {
                "id": r[0],
                "usuario": r[1],
                "expresion": r[2],
                "es_valida": bool(r[3]),
                "resultado": r[4],
                "error": r[5],
                "fecha_hora": r[6],
            }
            for r in rows
        ]


class ExportImportService:
    def __init__(self, eval_repo: EvaluacionRepository) -> None:
        self.repo = eval_repo

    def exportar_json(self, ruta: str, usuario_id: int | None = None) -> str:
        registros = self.repo.consultar_historial(usuario_id)
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump({"evaluaciones": registros}, f, ensure_ascii=False, indent=2, default=str)
        return ruta

    def exportar_xml(self, ruta: str, usuario_id: int | None = None) -> str:
        registros = self.repo.consultar_historial(usuario_id)
        root = ET.Element("evaluaciones")
        for r in registros:
            nodo = ET.SubElement(root, "evaluacion")
            for clave, valor in r.items():
                hijo = ET.SubElement(nodo, clave)
                hijo.text = str(valor) if valor is not None else ""
        tree = ET.ElementTree(root)
        ET.indent(tree, space="  ")
        tree.write(ruta, encoding="utf-8", xml_declaration=True)
        return ruta

    def importar_json(self, ruta: str, usuario_id: int, reevaluar: bool = False) -> list[dict]:
        from evaluator import Evaluador
        evaluar = Evaluador().evaluar
        with open(ruta, "r", encoding="utf-8") as f:
            datos = json.load(f)
        resultados = []
        for item in datos.get("evaluaciones", []):
            expresion = item.get("expresion", "")
            if reevaluar:
                r = evaluar(expresion)
                self.repo.guardar(usuario_id, r)
                resultados.append(r)
            else:
                resultados.append(item)
        return resultados

    def importar_xml(self, ruta: str, usuario_id: int, reevaluar: bool = False) -> list[dict]:
        from evaluator import Evaluador
        evaluar = Evaluador().evaluar
        tree = ET.parse(ruta)
        root = tree.getroot()
        resultados = []
        for nodo in root.findall("evaluacion"):
            expresion = nodo.findtext("expresion", default="")
            if reevaluar:
                r = evaluar(expresion)
                self.repo.guardar(usuario_id, r)
                resultados.append(r)
            else:
                resultados.append({child.tag: child.text for child in nodo})
        return resultados


class SistemaEvaluaciones:
    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db = DatabaseManager(db_path)
        self.usuarios = UsuarioRepository(self.db)
        self.evaluaciones = EvaluacionRepository(self.db)
        self.exportar = ExportImportService(self.evaluaciones)
        self.importar = self.exportar  # mismo servicio para ambas funciones

    def inicializar(self) -> None:
        self.db.inicializar()
