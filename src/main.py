"""
main_gui.py
Interfaz gráfica con PySide6 para el Evaluador de Expresiones Matemáticas.
Ventanas: LoginWindow → MainWindow
Proyecto: Evaluador de Expresiones Matemáticas — Equipo 5

"""

import sys
import time
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QDialog,
    QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QMessageBox, QHeaderView,
    QFrame, QFileDialog,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor

from db_manager import SistemaEvaluaciones
from evaluator import Evaluador

ESTILO_GLOBAL = """
    QWidget {
        background-color: #f4f6f9;
        font-family: Segoe UI, Arial, sans-serif;
        font-size: 13px;
        color: #2c3e50;
    }
    QLineEdit {
        background: #ffffff;
        border: 1px solid #ccd1d9;
        border-radius: 6px;
        padding: 6px 10px;
    }
    QLineEdit:focus {
        border: 1px solid #3498db;
    }
    QPushButton {
        border-radius: 6px;
        padding: 7px 18px;
        font-weight: bold;
    }
    QPushButton#btn_primary {
        background-color: #3498db;
        color: white;
        border: none;
    }
    QPushButton#btn_primary:hover  { background-color: #2980b9; }
    QPushButton#btn_primary:pressed{ background-color: #1a6fa3; }

    QPushButton#btn_secondary {
        background-color: #ecf0f1;
        color: #2c3e50;
        border: 1px solid #bdc3c7;
    }
    QPushButton#btn_secondary:hover  { background-color: #dfe6e9; }

    QPushButton#btn_danger {
        background-color: #e74c3c;
        color: white;
        border: none;
    }
    QPushButton#btn_danger:hover { background-color: #c0392b; }

    QTableWidget {
        background: #ffffff;
        border: 1px solid #dde1e7;
        border-radius: 6px;
        gridline-color: #ecf0f1;
    }
    QHeaderView::section {
        background-color: #2c3e50;
        color: white;
        padding: 6px;
        border: none;
        font-weight: bold;
    }
    QLabel#titulo {
        font-size: 20px;
        font-weight: bold;
        color: #2c3e50;
    }
    QLabel#subtitulo {
        font-size: 13px;
        color: #7f8c8d;
    }
    QFrame#card {
        background: #ffffff;
        border: 1px solid #dde1e7;
        border-radius: 10px;
    }
"""


class LoginWindow(QDialog):
    MAX_INTENTOS   = 3
    BLOQUEO_SEG    = 60

    def __init__(self, sistema: SistemaEvaluaciones) -> None:
        super().__init__()
        self._sistema        = sistema
        self.usuario_id: int | None = None
        self.username:   str        = ""
        self._intentos       = 0
        self._bloqueado_hasta: float = 0.0   # timestamp epoch
        self._timer          = QTimer(self)
        self._timer.setInterval(1000)        # cada 1 segundo
        self._timer.timeout.connect(self._actualizar_cuenta_regresiva)
        self._build_ui()

    def _build_ui(self) -> None:
        self.setWindowTitle("Acceso — Evaluador de Expresiones")
        self.setFixedSize(380, 460)
        self.setStyleSheet(ESTILO_GLOBAL)

        root = QVBoxLayout(self)
        root.setContentsMargins(40, 30, 40, 30)
        root.setSpacing(16)

        # ── encabezado ────────────────────────────────────────────────────────
        titulo = QLabel("Evaluador de\nExpresiones Matemáticas")
        titulo.setObjectName("titulo")
        titulo.setAlignment(Qt.AlignCenter)
        root.addWidget(titulo)

        sub = QLabel("Equipo 5 — Ingeniería de Software")
        sub.setObjectName("subtitulo")
        sub.setAlignment(Qt.AlignCenter)
        root.addWidget(sub)

        root.addSpacing(10)

        # ── formulario ────────────────────────────────────────────────────────
        form = QFormLayout()
        form.setSpacing(10)

        self._inp_user = QLineEdit()
        self._inp_user.setPlaceholderText("nombre de usuario")
        form.addRow("Usuario:", self._inp_user)

        self._inp_pass = QLineEdit()
        self._inp_pass.setPlaceholderText("contraseña")
        self._inp_pass.setEchoMode(QLineEdit.Password)
        self._inp_pass.returnPressed.connect(self._on_login)
        form.addRow("Contraseña:", self._inp_pass)

        root.addLayout(form)
        root.addSpacing(6)

        # ── etiqueta de estado (errores / bloqueo / éxito) ────────────────────
        self._lbl_error = QLabel("")
        self._lbl_error.setAlignment(Qt.AlignCenter)
        self._lbl_error.setWordWrap(True)
        self._lbl_error.setStyleSheet("color: #e74c3c; font-size: 12px;")
        root.addWidget(self._lbl_error)

        # ── etiqueta de intentos restantes ────────────────────────────────────
        self._lbl_intentos = QLabel("")
        self._lbl_intentos.setAlignment(Qt.AlignCenter)
        self._lbl_intentos.setStyleSheet("color: #e67e22; font-size: 11px;")
        root.addWidget(self._lbl_intentos)

        # ── botones ───────────────────────────────────────────────────────────
        self._btn_login = QPushButton("Iniciar sesión")
        self._btn_login.setObjectName("btn_primary")
        self._btn_login.clicked.connect(self._on_login)

        btn_reg = QPushButton("Registrarse")
        btn_reg.setObjectName("btn_secondary")
        btn_reg.clicked.connect(self._on_registrar)

        root.addWidget(self._btn_login)
        root.addWidget(btn_reg)
        root.addStretch()

    # ── lógica de bloqueo ─────────────────────────────────────────────────────
    def _esta_bloqueado(self) -> bool:
        return time.time() < self._bloqueado_hasta

    def _segundos_restantes(self) -> int:
        return max(0, int(self._bloqueado_hasta - time.time()))

    def _activar_bloqueo(self) -> None:
        self._bloqueado_hasta = time.time() + self.BLOQUEO_SEG
        self._inp_user.setEnabled(False)
        self._inp_pass.setEnabled(False)
        self._btn_login.setEnabled(False)
        self._timer.start()
        self._actualizar_cuenta_regresiva()

    def _desactivar_bloqueo(self) -> None:
        self._timer.stop()
        self._intentos = 0
        self._inp_user.setEnabled(True)
        self._inp_pass.setEnabled(True)
        self._btn_login.setEnabled(True)
        self._lbl_error.setStyleSheet("color: #e74c3c; font-size: 12px;")
        self._lbl_error.setText("")
        self._lbl_intentos.setText("")

    def _actualizar_cuenta_regresiva(self) -> None:
        seg = self._segundos_restantes()
        if seg <= 0:
            self._desactivar_bloqueo()
        else:
            self._lbl_error.setStyleSheet("color: #c0392b; font-size: 12px; font-weight: bold;")
            self._lbl_error.setText(
                f"🔒 Demasiados intentos fallidos.\n"
                f"Espera {seg} segundo{'s' if seg != 1 else ''} para continuar."
            )

    # ── lógica de autenticación ───────────────────────────────────────────────
    def _credenciales(self) -> tuple[str, str]:
        return self._inp_user.text().strip(), self._inp_pass.text()

    def _on_login(self) -> None:
        if self._esta_bloqueado():
            return

        user, pwd = self._credenciales()
        if not user or not pwd:
            self._lbl_error.setStyleSheet("color: #e74c3c; font-size: 12px;")
            self._lbl_error.setText("Completa usuario y contraseña.")
            return

        valido, uid = self._sistema.usuarios.autenticar(user, pwd)
        if valido:
            self.usuario_id = uid
            self.username   = user
            self.accept()
        else:
            self._intentos += 1
            restantes = self.MAX_INTENTOS - self._intentos

            if self._intentos >= self.MAX_INTENTOS:
                self._activar_bloqueo()
            else:
                self._lbl_error.setStyleSheet("color: #e74c3c; font-size: 12px;")
                self._lbl_error.setText("Credenciales incorrectas.")
                self._lbl_intentos.setText(
                    f"Intentos restantes: {restantes} de {self.MAX_INTENTOS}"
                )

    def _on_registrar(self) -> None:
        user, pwd = self._credenciales()
        ok, msg = self._sistema.usuarios.registrar(user, pwd)
        if ok:
            self._lbl_error.setStyleSheet("color: #27ae60; font-size: 12px;")
            self._lbl_error.setText("Registro exitoso. Ahora inicia sesión.")
            self._lbl_intentos.setText("")
        else:
            self._lbl_error.setStyleSheet("color: #e74c3c; font-size: 12px;")
            self._lbl_error.setText(msg)


class PasosDialog(QDialog):
    def __init__(self, resultado: dict, parent=None) -> None:
        super().__init__(parent)
        self._resultado = resultado
        self._build_ui()

    def _build_ui(self) -> None:
        expr = self._resultado['expresion']
        self.setWindowTitle("Paso a paso — " + expr)
        self.resize(600, 420)
        self.setStyleSheet(ESTILO_GLOBAL)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(12)

        # encabezado
        lbl = QLabel(f"Expresión:  <b>{expr}</b>")
        lbl.setTextFormat(Qt.RichText)
        root.addWidget(lbl)

        pasos = self._resultado.get('pasos', [])

        if not pasos:
            root.addWidget(QLabel("No hay pasos disponibles (expresión inválida)."))
        else:
            # tabla de pasos
            tabla = QTableWidget()
            tabla.setColumnCount(3)
            tabla.setHorizontalHeaderLabels(["Token", "Pila operandos", "Pila operadores"])
            tabla.setRowCount(len(pasos))
            tabla.setEditTriggers(QTableWidget.NoEditTriggers)
            tabla.setSelectionBehavior(QTableWidget.SelectRows)
            tabla.verticalHeader().setVisible(False)
            hdr = tabla.horizontalHeader()
            hdr.setSectionResizeMode(0, QHeaderView.ResizeToContents)
            hdr.setSectionResizeMode(1, QHeaderView.Stretch)
            hdr.setSectionResizeMode(2, QHeaderView.Stretch)

            COLORES = {
                'numero'   : QColor("#eaf4fb"),
                'abre'     : QColor("#fef9e7"),
                'cierra'   : QColor("#fef9e7"),
                'operador' : QColor("#f9ebea"),
            }

            for i, paso in enumerate(pasos):
                token = paso['token']
                ops   = paso['operandos']
                opers = paso['operadores']

                # formato legible de las pilas (tope a la derecha)
                str_ops   = "  ←  ".join(
                    str(int(v) if v == int(v) else round(v, 4)) for v in ops
                ) if ops else "[ vacía ]"
                str_opers = "  ←  ".join(opers) if opers else "[ vacía ]"

                # color por tipo de token
                if token in ('+', '-', '*', '/', '^'):
                    color = COLORES['operador']
                elif token in ('(', '[', '{'):
                    color = COLORES['abre']
                elif token in (')', ']', '}'):
                    color = COLORES['cierra']
                else:
                    color = COLORES['numero']

                for col, texto in enumerate([token, str_ops, str_opers]):
                    item = QTableWidgetItem(texto)
                    item.setBackground(color)
                    item.setTextAlignment(Qt.AlignCenter if col == 0 else Qt.AlignLeft | Qt.AlignVCenter)
                    tabla.setItem(i, col, item)

            root.addWidget(tabla)

        # resultado final
        if self._resultado['valida']:
            lbl_res = QLabel(f"✅  Resultado final: <b>{self._resultado['resultado']}</b>")
            lbl_res.setStyleSheet("color: #27ae60; font-size: 13px;")
        else:
            lbl_res = QLabel(f"❌  {self._resultado['error']}")
            lbl_res.setStyleSheet("color: #e74c3c; font-size: 13px;")
        lbl_res.setTextFormat(Qt.RichText)
        root.addWidget(lbl_res)

        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.setObjectName("btn_primary")
        btn_cerrar.clicked.connect(self.accept)
        root.addWidget(btn_cerrar, alignment=Qt.AlignRight)

class MainWindow(QMainWindow):
    def __init__(
        self,
        sistema: SistemaEvaluaciones,
        evaluador: Evaluador,
        usuario_id: int,
        username: str,
    ) -> None:
        super().__init__()
        self._sistema    = sistema
        self._evaluador  = evaluador
        self._usuario_id = usuario_id
        self._username   = username
        self._ultimo_resultado: dict | None = None
        self._historial_visible: bool = False
        self._build_ui()

    def _build_ui(self) -> None:
        self.setWindowTitle("Evaluador de Expresiones Matemáticas — Equipo 5")
        self.resize(820, 580)
        self.setStyleSheet(ESTILO_GLOBAL)

        central = QWidget()
        self.setCentralWidget(central)
        main = QVBoxLayout(central)
        main.setContentsMargins(20, 16, 20, 16)
        main.setSpacing(14)

        # ── barra superior ────────────────────────────────────────────────────
        barra = QHBoxLayout()
        lbl_titulo = QLabel("Evaluador de Expresiones")
        lbl_titulo.setObjectName("titulo")
        barra.addWidget(lbl_titulo)
        barra.addStretch()
        lbl_user = QLabel(f"👤  {self._username}")
        lbl_user.setObjectName("subtitulo")
        barra.addWidget(lbl_user)
        btn_salir = QPushButton("Cerrar sesión")
        btn_salir.setObjectName("btn_secondary")
        btn_salir.clicked.connect(self._on_cerrar_sesion)
        barra.addWidget(btn_salir)
        main.addLayout(barra)

        # ── separador ─────────────────────────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #dde1e7;")
        main.addWidget(sep)

        # ── card: entrada de expresión ────────────────────────────────────────
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 14, 16, 14)
        card_layout.setSpacing(10)

        lbl_entrada = QLabel("Expresión matemática")
        lbl_entrada.setStyleSheet("font-weight: bold;")
        card_layout.addWidget(lbl_entrada)

        fila = QHBoxLayout()
        self._inp_expr = QLineEdit()
        self._inp_expr.setPlaceholderText("Ej: ( 2 + 3 ) * 4   ·   tokens separados por espacios")
        self._inp_expr.returnPressed.connect(self._on_evaluar)
        fila.addWidget(self._inp_expr)

        btn_eval = QPushButton("Evaluar")
        btn_eval.setObjectName("btn_primary")
        btn_eval.setMinimumWidth(100)
        btn_eval.clicked.connect(self._on_evaluar)
        fila.addWidget(btn_eval)

        self._btn_pasos = QPushButton("Ver pasos")
        self._btn_pasos.setObjectName("btn_secondary")
        self._btn_pasos.setMinimumWidth(100)
        self._btn_pasos.setEnabled(False)
        self._btn_pasos.clicked.connect(self._on_ver_pasos)
        fila.addWidget(self._btn_pasos)
        card_layout.addLayout(fila)

        # resultado
        self._lbl_resultado = QLabel("")
        self._lbl_resultado.setWordWrap(True)
        self._lbl_resultado.setMinimumHeight(28)
        self._lbl_resultado.setStyleSheet(
            "font-size: 14px; font-weight: bold; padding: 4px 0;"
        )
        card_layout.addWidget(self._lbl_resultado)

        main.addWidget(card)

        # ── historial ─────────────────────────────────────────────────────────
        from PySide6.QtWidgets import QCheckBox
        fila_hist = QHBoxLayout()
        lbl_hist = QLabel("Historial de evaluaciones")
        lbl_hist.setStyleSheet("font-weight: bold; font-size: 13px;")
        fila_hist.addWidget(lbl_hist)
        fila_hist.addStretch()
        self._chk_solo_validas = QCheckBox("Solo válidas")
        self._chk_solo_validas.setToolTip("Oculta las expresiones con error")
        self._chk_solo_validas.setVisible(False)
        self._chk_solo_validas.stateChanged.connect(self._cargar_historial)
        fila_hist.addWidget(self._chk_solo_validas)
        self._btn_toggle_hist = QPushButton("▶ Mostrar historial")
        self._btn_toggle_hist.setObjectName("btn_secondary")
        self._btn_toggle_hist.clicked.connect(self._on_toggle_historial)
        fila_hist.addWidget(self._btn_toggle_hist)
        main.addLayout(fila_hist)

        self._tabla = QTableWidget()
        self._tabla.setColumnCount(5)
        self._tabla.setHorizontalHeaderLabels(
            ["#", "Expresión", "Válida", "Resultado / Error", "Fecha y hora"]
        )
        self._tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        self._tabla.setSelectionBehavior(QTableWidget.SelectRows)
        self._tabla.verticalHeader().setVisible(False)
        hdr = self._tabla.horizontalHeader()
        hdr.setSectionResizeMode(1, QHeaderView.Stretch)
        hdr.setSectionResizeMode(3, QHeaderView.Stretch)
        self._tabla.setColumnWidth(0, 40)
        self._tabla.setColumnWidth(2, 60)
        self._tabla.setColumnWidth(4, 150)
        self._tabla.setVisible(False)
        main.addWidget(self._tabla)

        # ── fila de botones inferiores ────────────────────────────────────────
        from PySide6.QtWidgets import QMenu

        self._widget_bot = QWidget()
        fila_bot = QHBoxLayout(self._widget_bot)
        fila_bot.setContentsMargins(0, 0, 0, 0)

        # Botón Exportar con menú desplegable
        btn_exportar = QPushButton("⬇ Exportar")
        btn_exportar.setObjectName("btn_secondary")
        menu_exp = QMenu(btn_exportar)
        menu_exp.addAction("JSON (.json)", lambda: self._on_exportar("json"))
        menu_exp.addAction("XML  (.xml)",  lambda: self._on_exportar("xml"))
        btn_exportar.setMenu(menu_exp)

        # Botón Importar con menú desplegable
        btn_importar = QPushButton("⬆ Importar")
        btn_importar.setObjectName("btn_secondary")
        menu_imp = QMenu(btn_importar)
        menu_imp.addAction("JSON (.json)", lambda: self._on_importar("json"))
        menu_imp.addAction("XML  (.xml)",  lambda: self._on_importar("xml"))
        btn_importar.setMenu(menu_imp)

        btn_del = QPushButton("🗑 Eliminar selección")
        btn_del.setObjectName("btn_danger")
        btn_del.clicked.connect(self._on_eliminar)

        fila_bot.addWidget(btn_exportar)
        fila_bot.addWidget(btn_importar)
        fila_bot.addStretch()
        fila_bot.addWidget(btn_del)

        self._widget_bot.setVisible(False)
        main.addWidget(self._widget_bot)

    # ── lógica: evaluar ───────────────────────────────────────────────────────
    def _on_evaluar(self) -> None:
        expr = self._inp_expr.text().strip()
        if not expr:
            return

        # Verificar duplicado antes de evaluar o guardar
        historial = self._sistema.evaluaciones.consultar_historial(self._usuario_id)
        if any(r['expresion'] == expr for r in historial):
            self._lbl_resultado.setStyleSheet(
                "font-size: 14px; font-weight: bold; color: #e67e22;"
            )
            self._lbl_resultado.setText(f"⚠️  Expresión duplicada: '{expr}' ya está en el historial.")
            self._inp_expr.clear()
            return

        r = self._evaluador.evaluar(expr)
        self._sistema.evaluaciones.guardar(self._usuario_id, r)
        self._ultimo_resultado = r
        self._btn_pasos.setEnabled(True)

        if r['valida']:
            self._lbl_resultado.setStyleSheet(
                "font-size: 14px; font-weight: bold; color: #27ae60;"
            )
            self._lbl_resultado.setText(f"✅  Resultado: {r['resultado']}")
        else:
            self._lbl_resultado.setStyleSheet(
                "font-size: 14px; font-weight: bold; color: #e74c3c;"
            )
            self._lbl_resultado.setText(f"❌  {r['error']}")

        self._inp_expr.clear()
        self._cargar_historial()

    # ── lógica: ver pasos ─────────────────────────────────────────────────────
    def _on_ver_pasos(self) -> None:
        if self._ultimo_resultado is None:
            return
        dialogo = PasosDialog(self._ultimo_resultado, parent=self)
        dialogo.exec()

    # ── lógica: toggle historial ──────────────────────────────────────────────
    def _on_toggle_historial(self) -> None:
        self._historial_visible = not self._historial_visible
        self._tabla.setVisible(self._historial_visible)
        self._widget_bot.setVisible(self._historial_visible)
        if self._historial_visible:
            self._btn_toggle_hist.setText("▼ Ocultar historial")
            self._chk_solo_validas.setVisible(True)
            self._cargar_historial()
        else:
            self._btn_toggle_hist.setText("▶ Mostrar historial")
            self._chk_solo_validas.setVisible(False)

    # ── lógica: historial ─────────────────────────────────────────────────────
    def _cargar_historial(self) -> None:
        if not self._historial_visible:
            return
        registros = self._sistema.evaluaciones.consultar_historial(self._usuario_id)

        if self._chk_solo_validas.isChecked():
            registros = [r for r in registros if r['es_valida']]

        self._tabla.setRowCount(len(registros))

        for fila, r in enumerate(registros):
            valida   = r['es_valida']
            contenido = r['resultado'] if valida else r['error']
            color     = QColor("#eafaf1") if valida else QColor("#fdf2f2")

            items = [
                str(r['id']),
                r['expresion'],
                "✅" if valida else "❌",
                contenido or "",
                r['fecha_hora'],
            ]
            for col, texto in enumerate(items):
                item = QTableWidgetItem(texto)
                item.setBackground(color)
                if col in (0, 2):
                    item.setTextAlignment(Qt.AlignCenter)
                self._tabla.setItem(fila, col, item)

    # ── lógica: eliminar ──────────────────────────────────────────────────────
    def _on_eliminar(self) -> None:
        filas = self._tabla.selectionModel().selectedRows()
        if not filas:
            QMessageBox.information(self, "Aviso", "Selecciona una fila para eliminar.")
            return

        fila_idx = filas[0].row()
        eval_id  = int(self._tabla.item(fila_idx, 0).text())

        resp = QMessageBox.question(
            self, "Confirmar",
            f"¿Eliminar la evaluación #{eval_id}?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if resp == QMessageBox.Yes:
            self._sistema.evaluaciones.eliminar(eval_id)
            self._cargar_historial()

    # ── lógica: exportar ──────────────────────────────────────────────────────
    def _on_exportar(self, formato: str) -> None:
        filtro  = "Archivos JSON (*.json)" if formato == "json" else "Archivos XML (*.xml)"
        defecto = f"historial_{self._username}.{formato}"
        ruta, _ = QFileDialog.getSaveFileName(self, "Exportar historial", defecto, filtro)
        if not ruta:
            return
        try:
            if formato == "json":
                self._sistema.exportar.exportar_json(ruta, self._usuario_id)
            else:
                self._sistema.exportar.exportar_xml(ruta, self._usuario_id)
            QMessageBox.information(self, "Exportación exitosa", f"Historial exportado en:\n{ruta}")
        except Exception as e:
            QMessageBox.critical(self, "Error al exportar", str(e))

    # ── lógica: importar ──────────────────────────────────────────────────────
    def _on_importar(self, formato: str) -> None:
        filtro = "Archivos JSON (*.json)" if formato == "json" else "Archivos XML (*.xml)"
        ruta, _ = QFileDialog.getOpenFileName(self, "Importar historial", "", filtro)
        if not ruta:
            return
        try:
            if formato == "json":
                registros = self._sistema.exportar.importar_json(ruta, self._usuario_id)
            else:
                registros = self._sistema.exportar.importar_xml(ruta, self._usuario_id)

            # Evaluar y guardar cada expresión, omitiendo duplicados
            historial_actual = {r['expresion'] for r in self._sistema.evaluaciones.consultar_historial(self._usuario_id)}
            guardados = 0
            duplicados = 0
            for item in registros:
                expr = item.get('expresion', '').strip()
                if not expr:
                    continue
                if expr in historial_actual:
                    duplicados += 1
                    continue
                r = self._evaluador.evaluar(expr)
                self._sistema.evaluaciones.guardar(self._usuario_id, r)
                historial_actual.add(expr)
                guardados += 1

            self._cargar_historial()

            resumen = f"Importados: {guardados} registro(s)."
            if duplicados:
                resumen += f"\nOmitidos por duplicado: {duplicados}."
            QMessageBox.information(self, "Importación exitosa", resumen)

        except Exception as e:
            QMessageBox.critical(self, "Error al importar", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Error al importar", str(e))

    # ── cerrar sesión ─────────────────────────────────────────────────────────
    def _on_cerrar_sesion(self) -> None:
        self.close()

def main() -> None:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Inicializar BD y lógica
    sistema   = SistemaEvaluaciones()
    sistema.inicializar()
    evaluador = Evaluador()

    # Mostrar login
    login = LoginWindow(sistema)
    if login.exec() != QDialog.Accepted:
        sys.exit(0)

    # Abrir ventana principal
    ventana = MainWindow(sistema, evaluador, login.usuario_id, login.username)
    ventana.show()

    # Al cerrar la ventana principal, volver al login
    while True:
        app.exec()
        login2 = LoginWindow(sistema)
        if login2.exec() != QDialog.Accepted:
            break
        ventana = MainWindow(sistema, evaluador, login2.usuario_id, login2.username)
        ventana.show()


if __name__ == "__main__":
    main()