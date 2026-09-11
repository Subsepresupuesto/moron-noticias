"""Motor de filtrado y priorización (Anexo I, puntos 1 y 3).

Orden de evaluación sobre el texto normalizado de cada nota:

1. **Compuerta**: la nota debe contener «morón». Si no, se descarta.
2. **Términos**: además debe coincidir al menos un término de Nivel A o de Nivel B.
3. **Etiquetado**: se registran el/los niveles detectados y la lista de términos
   que coincidieron.

Los niveles se conservan solo como etiqueta de prioridad visual; ninguno
condiciona por sí solo el ingreso. No hay alertas en tiempo real.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .config import ConfigMonitoreo, TerminoCfg
from .normalize import normalizar, tokenizar

MOTIVO_SIN_MORON = "sin_moron"
MOTIVO_SIN_TERMINOS = "sin_terminos"
MOTIVO_ACEPTADA = "aceptada"

_SEPARADOR_ORACION = re.compile(r"[.!?\n]+")


def _oraciones(texto_normalizado: str) -> list[str]:
    """Parte un texto ya normalizado (con puntuación) en oraciones."""
    return [o.strip() for o in _SEPARADOR_ORACION.split(texto_normalizado) if o.strip()]


@dataclass(frozen=True)
class Coincidencia:
    termino_id: str
    nivel: str
    patron: str
    ocurrencias: int
    etiqueta_especial: str | None = None


@dataclass(frozen=True)
class ResultadoFiltrado:
    aceptada: bool
    motivo: str
    niveles: tuple[str, ...] = ()
    coincidencias: tuple[Coincidencia, ...] = ()

    def ids_terminos(self) -> list[str]:
        return [c.termino_id for c in self.coincidencias]

    def etiquetas_especiales(self) -> list[str]:
        return [c.etiqueta_especial for c in self.coincidencias if c.etiqueta_especial]


# ---------------------------------------------------------------------------
# Búsquedas a nivel de token
# ---------------------------------------------------------------------------
def _indices_sublista(tokens: list[str], patron: list[str]) -> list[int]:
    """Índices de inicio donde ``patron`` aparece como sublista contigua de ``tokens``."""
    if not patron:
        return []
    n, m = len(tokens), len(patron)
    return [i for i in range(n - m + 1) if tokens[i : i + m] == patron]


def _indices_prefijo(tokens: list[str], prefijo: str) -> list[int]:
    return [i for i, t in enumerate(tokens) if t.startswith(prefijo)]


class MotorFiltrado:
    """Aplica la lógica de filtrado a partir de una :class:`ConfigMonitoreo`."""

    def __init__(self, config: ConfigMonitoreo) -> None:
        self.config = config
        self._ventana = config.context_window_words
        # Cada término de la compuerta, ya normalizado y partido en tokens.
        self._compuerta: list[list[str]] = [
            tokenizar(normalizar(t)) for t in config.compuerta
        ]
        self._compuerta_excluye = [normalizar(f) for f in config.compuerta_excluye_contexto if f]

    # ------------------------------------------------------------------
    def evaluar(self, titulo: str = "", cuerpo: str = "") -> ResultadoFiltrado:
        texto_normalizado = normalizar(f"{titulo}\n{cuerpo}")
        tokens = tokenizar(texto_normalizado)

        if not self._pasa_compuerta(texto_normalizado):
            return ResultadoFiltrado(aceptada=False, motivo=MOTIVO_SIN_MORON)

        coincidencias: list[Coincidencia] = []
        for nivel in self.config.niveles:
            for term in nivel.terminos:
                oc = self._contar_termino(term, tokens)
                if oc > 0:
                    coincidencias.append(
                        Coincidencia(
                            termino_id=term.id,
                            nivel=nivel.clave,
                            patron=term.patron,
                            ocurrencias=oc,
                            etiqueta_especial=term.etiqueta_especial,
                        )
                    )

        # Por defecto la nota debe coincidir con algún término de nivel además de
        # la compuerta (lógica Morón). Si el config marca exigir_termino=False,
        # basta con pasar la compuerta y los niveles quedan solo como etiquetas.
        if not coincidencias and getattr(self.config, "exigir_termino", True):
            return ResultadoFiltrado(aceptada=False, motivo=MOTIVO_SIN_TERMINOS)

        niveles = tuple(sorted({c.nivel for c in coincidencias}))
        return ResultadoFiltrado(
            aceptada=True,
            motivo=MOTIVO_ACEPTADA,
            niveles=niveles,
            coincidencias=tuple(coincidencias),
        )

    # ------------------------------------------------------------------
    def _pasa_compuerta(self, texto_normalizado: str) -> bool:
        """La compuerta se evalúa oración por oración (no por ventana de
        palabras): una mención cuenta si, en ESA oración, no está acompañada de
        una frase de exclusión (p. ej. "a 70 kilómetros de Morón", "cómo llegar
        desde Morón, Castelar..." — referencias de distancia/ruta, típicas de
        notas turísticas de otras localidades que solo usan a Morón como punto
        geográfico). Si alguna otra oración menciona a Morón sin ese contexto,
        la nota entra igual.
        """
        patrones = [p for p in self._compuerta if p]
        if not patrones:
            return False
        for oracion in _oraciones(texto_normalizado):
            oracion_tokens = tokenizar(oracion)
            if not any(_indices_sublista(oracion_tokens, patron) for patron in patrones):
                continue
            if not self._compuerta_excluye or not any(f in oracion for f in self._compuerta_excluye):
                return True
        return False

    def _contar_termino(self, term: TerminoCfg, tokens: list[str]) -> int:
        patron_norm = normalizar(term.patron)

        # Forma directa por nombre completo (p. ej. «guido napolitano»).
        if term.coincide_directo_si_frase:
            frase = tokenizar(normalizar(term.coincide_directo_si_frase))
            hits = _indices_sublista(tokens, frase)
            if hits:
                return len(hits)

        if term.modo == "prefix":
            indices = _indices_prefijo(tokens, patron_norm.replace(" ", ""))
            largo_patron = 1
        elif term.modo == "substring":
            texto = " ".join(tokens)
            return texto.count(patron_norm) if patron_norm else 0
        else:  # "word" / "phrase" -> coincidencia de sublista de tokens
            patron_tokens = tokenizar(patron_norm)
            indices = _indices_sublista(tokens, patron_tokens)
            largo_patron = len(patron_tokens)

        if not indices:
            return 0
        if not term.requiere_contexto:
            return len(indices)

        # Requiere contexto: contar solo las ocurrencias con un término de
        # contexto dentro de la ventana de palabras.
        contexto = [normalizar(c) for c in term.contexto_any]
        validas = 0
        for pos in indices:
            ini = max(0, pos - self._ventana)
            fin = min(len(tokens), pos + largo_patron + self._ventana)
            ventana_txt = " ".join(tokens[ini:fin])
            if any(c and c in ventana_txt for c in contexto):
                validas += 1
        return validas
