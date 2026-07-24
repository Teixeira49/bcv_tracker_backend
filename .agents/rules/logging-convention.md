---
description: Obliga a usar logging estructurado (api/core/logging/logger.py) en lugar de print() en todo el código de api/. Aplica cada vez que se registre un evento, error o diagnóstico en el backend.
---
# Convención de Logging

El proyecto diagnostica incidencias con **logging estructurado y con niveles**, no con `print()`. Un `print()` va a stdout sin nivel, sin timestamp ni contexto, y no se puede filtrar ni silenciar por entorno; en producción (serverless/Vercel) eso equivale a perder trazabilidad. Esta regla mantiene los logs consistentes y accionables.

## Regla

1. **Nunca uses `print()`** en `api/` para registrar eventos, errores o diagnósticos.
2. Obtén un logger con el factory central:
   ```python
   from api.core.logging.logger import get_logger

   logger = get_logger("services.dollar")  # namespace del módulo
   ```
   El logger cuelga del namespace del proyecto (`Constants.LOGGER_NAMESPACE`) y se configura en un solo punto (`configure_logging()`, invocado en el arranque de `api/main.py`).
3. **Elige el nivel por semántica**:
   - `logger.debug(...)`: detalle de desarrollo/diagnóstico fino.
   - `logger.info(...)`: eventos normales del ciclo de vida.
   - `logger.warning(...)`: algo inesperado pero recuperable (degradación elegante).
   - `logger.error(...)`: un fallo que impide completar una operación.
   - `logger.exception(...)`: **dentro de un `except`**, registra el mensaje + el traceback completo (equivale a `error` con `exc_info=True`).
4. **No formatees el mensaje con f-strings** si puedes usar los args perezosos del logger:
   ```python
   logger.error("No se pudo leer %s", source)   # ✅ se formatea solo si el nivel aplica
   ```
5. **No filtres secretos** en los logs (URLs con credenciales, tokens, valores de env vars): registra solo lo necesario para diagnosticar.

## Configuración por entorno

El nivel se controla con la variable de entorno **`LOG_LEVEL`** (`DEBUG`/`INFO`/`WARNING`/`ERROR`/`CRITICAL`; `INFO` por defecto). El formato y el namespace están centralizados en `Constants` (`LOG_FORMAT`, `LOG_DATE_FORMAT`, `LOGGER_NAMESPACE`). Ver `environment-variables.md` para la sincronización de `LOG_LEVEL`.

## Verificación (CI)

El test `tests/test_no_print_in_api.py` recorre `api/` con el AST y **falla si aparece un `print(...)`**. Corre en la suite de `pytest` (local y CI, `.github/workflows/tests.yml`), de modo que una regresión que reintroduzca `print()` no puede mergearse.
