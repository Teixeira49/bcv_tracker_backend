"""Configuración compartida de la suite de pruebas.

Fija un ``DATABASE_URL`` en memoria (SQLite) antes de importar cualquier módulo
de ``api``, ya que ``api.services.bd_service`` exige la variable al importarse.
``create_engine`` es perezoso, así que no abre ninguna conexión real: basta con
que la variable exista para que los tests unitarios (que mockean la red y no
tocan la BD) puedan importar los servicios.
"""
import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
