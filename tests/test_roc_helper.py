"""Issue #21 (DRY): helper único de ROC (``Helper.rate_of_change``).

El cálculo de la variación porcentual estaba duplicado en
``save_currencies_to_db`` y en ``calculate_live_changes``. Ahora vive en un
único helper; estos tests fijan su contrato (fórmula y guard de división por
cero) para que ambos consumidores compartan el mismo comportamiento.
"""
import pytest

from api.utils.helpers.helper import Helper


helper = Helper()


def test_roc_variacion_positiva():
    # de 100 a 110 -> +10%
    assert helper.rate_of_change(100.0, 110.0) == pytest.approx(10.0)


def test_roc_variacion_negativa():
    # de 200 a 150 -> -25%
    assert helper.rate_of_change(200.0, 150.0) == pytest.approx(-25.0)


def test_roc_sin_cambio_es_cero():
    assert helper.rate_of_change(100.0, 100.0) == 0.0


@pytest.mark.parametrize("previous", [0, 0.0, None])
def test_roc_sin_base_devuelve_cero(previous):
    """Sin valor previo (0 o None) no hay base de comparación -> 0.0, sin ZeroDivisionError."""
    assert helper.rate_of_change(previous, 123.45) == 0.0
