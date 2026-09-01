import pytest

from monitoreo.config import ConfigMonitoreo
from monitoreo.filtering import (
    MOTIVO_ACEPTADA,
    MOTIVO_SIN_MORON,
    MOTIVO_SIN_TERMINOS,
    MotorFiltrado,
)


@pytest.fixture(scope="module")
def motor() -> MotorFiltrado:
    # Se carga la configuración real que se despliega: las pruebas la validan de paso.
    return MotorFiltrado(ConfigMonitoreo.desde_yaml())


# --- Compuerta ------------------------------------------------------------
def test_sin_moron_se_descarta(motor):
    r = motor.evaluar(
        titulo="Comienza una obra en Hurlingham",
        cuerpo="El municipio destinó presupuesto de la Secretaría de Economía a la obra.",
    )
    assert r.aceptada is False
    assert r.motivo == MOTIVO_SIN_MORON
    assert r.niveles == ()


def test_moron_sin_terminos_se_descarta(motor):
    r = motor.evaluar(
        titulo="Morón inauguró una plaza",
        cuerpo="Vecinos del municipio de Morón disfrutaron del nuevo espacio verde.",
    )
    assert r.aceptada is False
    assert r.motivo == MOTIVO_SIN_TERMINOS


def test_compuerta_sin_tilde(motor):
    r = motor.evaluar(cuerpo="Vecinos de Moron reclaman por el presupuesto municipal.")
    assert r.aceptada is True
    assert r.motivo == MOTIVO_ACEPTADA


# --- Nivel B -----------------------------------------------------------
def test_nivel_b_presupuesto(motor):
    r = motor.evaluar(titulo="Morón aprobó su presupuesto 2026", cuerpo="Detalle de partidas.")
    assert r.aceptada is True
    assert r.niveles == ("B",)
    assert "presupuesto" in r.ids_terminos()


def test_nivel_b_raiz_economica(motor):
    r = motor.evaluar(cuerpo="La situación económica de Morón preocupa a los comerciantes.")
    assert r.aceptada is True
    assert "economia_raiz" in r.ids_terminos()
    assert r.niveles == ("B",)


def test_nivel_b_recursos_humanos_frase(motor):
    r = motor.evaluar(cuerpo="Conflicto en Recursos Humanos del municipio de Morón.")
    assert r.aceptada is True
    assert "recursos_humanos" in r.ids_terminos()


def test_secretaria_de_economia_etiqueta_especial(motor):
    r = motor.evaluar(cuerpo="La Secretaría de Economía de Morón difundió el informe mensual.")
    assert r.aceptada is True
    assert "secretaria_de_economia" in r.ids_terminos()
    assert "economia.secretaria" in r.etiquetas_especiales()


def test_planificacion_presupuestaria(motor):
    r = motor.evaluar(
        cuerpo="La Subsecretaría de Planificación Presupuestaria de Morón revisó las metas."
    )
    assert r.aceptada is True
    ids = r.ids_terminos()
    assert "planificacion_presupuestaria" in ids
    assert "subsecretaria_planificacion_presupuestaria" in ids


# --- Nivel A -----------------------------------------------------------
def test_nivel_a_ghi(motor):
    r = motor.evaluar(cuerpo="El intendente Ghi recorrió las obras en Morón.")
    assert r.aceptada is True
    assert r.niveles == ("A",)
    assert "ghi" in r.ids_terminos()


def test_ghi_no_matchea_como_subcadena(motor):
    # "ghirlanda" no debe activar el término "ghi" (límite de palabra).
    r = motor.evaluar(cuerpo="La panadería Ghirlanda de Morón amplió su presupuesto de insumos.")
    assert "ghi" not in r.ids_terminos()
    # La nota igual entra por Nivel B (presupuesto).
    assert r.aceptada is True
    assert r.niveles == ("B",)


def test_napolitano_nombre_completo(motor):
    r = motor.evaluar(
        titulo="Presupuesto 2026",
        cuerpo="El intendente de Morón y Guido Napolitano presentaron el cálculo de recursos.",
    )
    assert r.aceptada is True
    assert "napolitano" in r.ids_terminos()
    assert "A" in r.niveles and "B" in r.niveles


def test_napolitano_apellido_con_contexto(motor):
    r = motor.evaluar(
        cuerpo="Napolitano encabezó el acto en Morón junto al secretario de Economía del distrito."
    )
    assert r.aceptada is True
    assert "napolitano" in r.ids_terminos()
    assert "A" in r.niveles


def test_napolitano_apellido_sin_contexto_no_matchea(motor):
    r = motor.evaluar(
        cuerpo="El vecino Roberto Napolitano vive en Morón desde hace treinta años."
    )
    assert "napolitano" not in r.ids_terminos()
    assert r.aceptada is False
    assert r.motivo == MOTIVO_SIN_TERMINOS


def test_pizza_napolitana_no_activa_el_apellido(motor):
    r = motor.evaluar(cuerpo="En Morón se consiguió la mejor pizza napolitana de la zona.")
    assert "napolitano" not in r.ids_terminos()


# --- Config -----------------------------------------------------------
def test_config_real_carga_medios_y_niveles():
    cfg = ConfigMonitoreo.desde_yaml()
    assert len(cfg.medios) == 11
    assert {n.clave for n in cfg.niveles} == {"A", "B"}
    assert cfg.compuerta == ("moron",)
    # Todos los medios tienen al menos un canal en el orden de preferencia.
    assert all(m.canales for m in cfg.medios)
