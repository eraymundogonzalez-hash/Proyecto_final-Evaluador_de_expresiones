# evaluator.py
# Módulo principal de lógica: tokenizador, validador de balanceo y evaluador de expresiones
# mediante algoritmo de DOS PILAS.
# Proyecto: Evaluador de Expresiones Matemáticas - Equipo 5
# Prohibido el uso de eval(). Tokens separados por espacios.

import re

PRECEDENCIA = {"+": 1, "-": 1, "*": 2, "/": 2, "^": 3}
ABRE  = {"(", "[", "{"}
CIERRA = {")", "]", "}"}
PARES = {")": "(", "]": "[", "}": "{"}


class Tokenizador:
    def tokenizar(self, expresion: str) -> list[str]:
        """Retorna la lista de tokens de la expresión.
        Elimina espacios dobles o accidentales."""
        return expresion.strip().split()

    @staticmethod
    def es_numero(token: str) -> bool:
        """Retorna True si el token representa un número (incluye negativos y decimales)."""
        try:
            float(token)
            return True
        except ValueError:
            return False


class ValidadorFormato:
    PATRON = re.compile(r"--")

    def validar_formato(self, expresion: str) -> tuple[bool, str]:
        if self.PATRON.search(expresion):
            return False, "Error de formato: los tokens deben estar separados por espacios."
        return True, "OK"


class ValidadorBalanceo:
    def validar_balanceo(self, tokens: list[str]) -> tuple[bool, str]:
        pila: list[str] = []
        for token in tokens:
            if token in ABRE:
                pila.append(token)
            elif token in CIERRA:
                if not pila:
                    return False, f"Error: token de cierre '{token}' sin apertura correspondiente."
                if pila[-1] != PARES[token]:
                    return False, (
                        f"Error: se esperaba cierre de '{pila[-1]}' "
                        f"pero se encontró '{token}'."
                    )
                pila.pop()
        if pila:
            return False, f"Error: '{pila[-1]}' abierto nunca fue cerrado."
        return True, "OK"


class Calculadora:
    def evaluar_tokens(self, tokens: list[str]) -> tuple[float, list[dict]]:
        pila_operandos: list[float] = []
        pila_operadores: list[str] = []
        pasos: list[dict] = []

        for token in tokens:
            if Tokenizador.es_numero(token):
                pila_operandos.append(float(token))
            elif token in ABRE:
                pila_operadores.append(token)
            elif token in CIERRA:
                abre_par = PARES[token]
                while pila_operadores and pila_operadores[-1] != abre_par:
                    self._aplicar_operacion(pila_operandos, pila_operadores)
                if not pila_operadores:
                    raise ValueError(f"Error estructural: no se encontró '{abre_par}'.")
                pila_operadores.pop()  # descartar el abre-agrupador
            elif token in PRECEDENCIA:
                while (
                    pila_operadores
                    and pila_operadores[-1] not in ABRE
                    and pila_operadores[-1] in PRECEDENCIA
                    and PRECEDENCIA[pila_operadores[-1]] >= PRECEDENCIA[token]
                ):
                    self._aplicar_operacion(pila_operandos, pila_operadores)
                pila_operadores.append(token)
            else:
                raise ValueError(f"Token desconocido: '{token}'")

            pasos.append({
                "token": token,
                "operandos": list(pila_operandos),
                "operadores": list(pila_operadores),
            })

        while pila_operadores:
            self._aplicar_operacion(pila_operandos, pila_operadores)

        if len(pila_operandos) != 1:
            raise ValueError("Error estructural: la expresión es ambigua o incompleta.")

        return pila_operandos[0], pasos

    @staticmethod
    def _aplicar_operacion(
        pila_operandos: list[float],
        pila_operadores: list[str],
    ) -> None:
        """Extrae el operador del tope y los dos operandos superiores,
        calcula el resultado y lo regresa a la pila de operandos.

        Raises:
            ValueError: división por cero u operador desconocido.
        """
        op = pila_operadores.pop()
        b  = pila_operandos.pop()
        a  = pila_operandos.pop()
        if   op == "+": res = a + b
        elif op == "-": res = a - b
        elif op == "*": res = a * b
        elif op == "/":
            if b == 0:
                raise ValueError("Error semántico: división por cero.")
            res = a / b
        elif op == "^": res = a ** b
        else:
            raise ValueError(f"Operador desconocido: '{op}'")
        pila_operandos.append(res)


class Evaluador:
    def __init__(self) -> None:
        self.fmt_validator = ValidadorFormato()
        self.bal_validator = ValidadorBalanceo()
        self.tokenizador   = Tokenizador()
        self.calculadora   = Calculadora()

    def evaluar(self, expresion: str) -> dict:
        resultado = {
            "expresion": expresion,
            "valida": False,
            "resultado": None,
            "error": None,
            "pasos": [],
        }

        # Paso 1: formato
        fmt_ok, fmt_msg = self.fmt_validator.validar_formato(expresion)
        if not fmt_ok:
            resultado["error"] = fmt_msg
            return resultado

        # Paso 2: tokenizar
        tokens = self.tokenizador.tokenizar(expresion)
        if not tokens:
            resultado["error"] = "Error: la expresión está vacía."
            return resultado

        # Paso 3: balanceo
        bal_ok, bal_msg = self.bal_validator.validar_balanceo(tokens)
        if not bal_ok:
            resultado["error"] = bal_msg
            return resultado

        # Paso 4: calcular
        try:
            valor, pasos = self.calculadora.evaluar_tokens(tokens)
            resultado["valida"]    = True
            resultado["resultado"] = valor
            resultado["pasos"]     = pasos
        except ValueError as e:
            resultado["error"] = str(e)

        return resultado

    def evaluar_lote(self, expresiones: list[str]) -> list[dict]:
        return [self.evaluar(expr) for expr in expresiones]
