"""DT-009: el parseo JSON de HttpClient tolera caracteres de control crudos.

Algunas fuentes P2P (p. ej. Bybit) devuelven anuncios cuyo texto libre incluye
saltos de línea o tabs **sin escapar** dentro de las cadenas JSON. El parseo
estricto (``response.json()``) reventaría con ``JSONDecodeError`` y tumbaría la
fuente de forma intermitente; ``HttpClient._parse_json`` usa ``strict=False``.
"""
import json

import pytest

from api.core.client.http_client import HttpClient


class _FakeResponse:
    def __init__(self, text):
        self.text = text


def test_parse_json_tolera_control_chars_crudos():
    # 'remark' con un salto de línea LITERAL dentro del string: JSON no estándar
    # pero real en respuestas de Bybit.
    raw = '{"result": {"items": [{"price": "827.5", "remark": "Pago rapido\nsolo bancos"}]}}'

    # Sanity: el parseo estricto (equivalente a response.json()) sí falla.
    with pytest.raises(json.JSONDecodeError):
        json.loads(raw)

    parsed = HttpClient._parse_json(_FakeResponse(raw))
    assert parsed["result"]["items"][0]["price"] == "827.5"


def test_parse_json_no_altera_json_valido():
    raw = '{"a": 1, "b": ["x", "y"], "c": {"d": 2.5}}'
    assert HttpClient._parse_json(_FakeResponse(raw)) == {"a": 1, "b": ["x", "y"], "c": {"d": 2.5}}
