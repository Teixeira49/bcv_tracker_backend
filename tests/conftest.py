"""Configuración compartida de la suite de pruebas.

Fija las variables de entorno requeridas por la app **antes** de importar
cualquier módulo de ``api``:

- ``DATABASE_URL`` en memoria (SQLite), porque ``api.services.bd_service`` la
  exige al importarse. ``create_engine`` es perezoso, así que no abre ninguna
  conexión real: basta con que la variable exista.
- Las URLs de las fuentes externas, porque ``api.main`` corre
  ``Config.validate()`` (fail-fast) al arrancar; sin ellas la app se montaría en
  modo *import error* y los routers de negocio no quedarían disponibles para los
  tests con ``TestClient``. Son URLs de marcador: los tests mockean la red y no
  llegan a golpearlas.
"""
import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("OFFICIAL_MARKET_DATA_PROVIDER_URL", "http://testserver.local")
os.environ.setdefault("MARKET_DATA_PROVIDER_A_URL", "http://testserver.local")
os.environ.setdefault("MARKET_DATA_PROVIDER_B_URL", "http://testserver.local")
os.environ.setdefault("MARKET_DATA_PROVIDER_C_URL", "http://testserver.local")
os.environ.setdefault("MARKET_DATA_PROVIDER_D_URL", "http://testserver.local")
