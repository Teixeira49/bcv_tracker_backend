"""Logging central y reutilizable del proyecto.

Este módulo es el **estándar** de logging de DolarTracker: todo el código nuevo
debe registrar eventos con ``get_logger(__name__)`` y los niveles del módulo
``logging`` (``info``/``warning``/``error``/``exception``) en lugar de usar
``print()`` (ver ``.agents/rules/logging-convention.md``).

- Los loggers cuelgan de un único namespace (``Constants.LOGGER_NAMESPACE``),
  de modo que se configuran en un solo punto sin pisar la config de uvicorn.
- El nivel es configurable por entorno con ``LOG_LEVEL`` (``INFO`` por defecto).
- El formato es estructurado y consistente (``Constants.LOG_FORMAT``).
"""

import logging

from api.core.config.config import Config
from api.utils.constants.constants import Constants as c


def configure_logging():
    """Configura el logging del proyecto una sola vez (idempotente).

    Aplica el nivel (``LOG_LEVEL`` del entorno, o ``INFO`` por defecto) y un
    handler con formato estructurado sobre el logger namespace del proyecto.
    Es seguro llamarla varias veces: no duplica handlers.

    :return: el logger raíz del namespace del proyecto ya configurado.
    """
    level_name = (Config.LOG_LEVEL or c.LOG_LEVEL_DEFAULT).strip().upper()
    level = getattr(logging, level_name, logging.INFO)

    root = logging.getLogger(c.LOGGER_NAMESPACE)
    root.setLevel(level)

    if not root.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(c.LOG_FORMAT, datefmt=c.LOG_DATE_FORMAT))
        root.addHandler(handler)

    # No propagar al root de logging para evitar líneas duplicadas cuando
    # uvicorn ya configura su propio handler en la raíz.
    root.propagate = False
    return root


def get_logger(name):
    """Devuelve un logger namespaced del proyecto (``dolartracker.<name>``).

    :param name: nombre del módulo/componente (habitualmente ``__name__``).
    """
    return logging.getLogger(f"{c.LOGGER_NAMESPACE}.{name}")
