"""Issue #29: config de Pydantic v2 (ConfigDict) en UpdateCurrenciesResponseData.

El schema usaba el estilo deprecado ``class Config: populate_by_name = True``.
Ahora usa ``model_config = ConfigDict(populate_by_name=True)``. Estos tests
fijan que:

- El modelo se puede poblar tanto por el **alias** (``updated_count``) como por
  el **nombre de campo** (``updated_currencies``).
- La config vive en ``model_config`` (API v2), no en un ``class Config`` (v1).
- Importar/instanciar el schema no dispara ``DeprecationWarning`` de Pydantic.
"""
import warnings

import pytest

from api.models.schemas import UpdateCurrenciesResponseData


def test_populate_by_alias():
    """Se puede construir con el alias `updated_count`."""
    model = UpdateCurrenciesResponseData(message="ok", updated_count=5)
    assert model.updated_currencies == 5
    assert model.model_dump(by_alias=True) == {"message": "ok", "updated_count": 5}


def test_populate_by_field_name():
    """Se puede construir con el nombre de campo `updated_currencies` (populate_by_name)."""
    model = UpdateCurrenciesResponseData(message="ok", updated_currencies=3)
    assert model.updated_currencies == 3


def test_uses_model_config_not_class_config():
    """La config es v2 (`model_config`), no el `class Config` v1 deprecado."""
    assert UpdateCurrenciesResponseData.model_config.get("populate_by_name") is True
    # En v2, `class Config` ya no debe existir como atributo del modelo.
    assert getattr(UpdateCurrenciesResponseData, "Config", None) is None


def test_no_pydantic_deprecation_warning():
    """Instanciar el schema no emite DeprecationWarning de Pydantic."""
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        UpdateCurrenciesResponseData(message="ok", updated_count=1)
