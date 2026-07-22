---
description: Al agregar o modificar un método de servicio, un endpoint o una fuente de tasa, obliga a documentarlo igual que el resto (docstring; summary/description/responses en OpenAPI; y sincronizar las listas ilustrativas de fuentes) en el MISMO cambio. Aplica cada vez que se toque la capa de servicios, los controllers o se sume una nueva plataforma.
---
# Documentación Uniforme de Código y OpenAPI

La documentación del proyecto (docstrings + Swagger/ReDoc) se mantiene **alineada al código y uniforme entre fuentes**: cada endpoint y cada método público se documenta igual que sus pares. La uniformización inicial la hizo DT-013 (issue #4); esta regla la vuelve repetible para que **todo lo nuevo nazca documentado como lo existente**, sin depender de un pase de limpieza posterior.

El riesgo concreto que evita: una fuente/endpoint nuevo que se agrega **después** de un pase de documentación queda con lagunas (fue exactamente lo que pasó con Airtm frente a DT-013 — endpoints sin docstring y ausente de las listas de fuentes). Ver el rol `documentation_agent` (`.agents/roles/documentation_agent.md`) para la misión y el estilo (docstrings estilo Google, type hints veraces, `examples` en Pydantic).

## Cuándo aplica

Cada vez que un cambio:
- **agregue o modifique un método público** en la capa de servicios (`api/services/*.py`) o transversal (`HttpClient`, `Helper`, `api_response`), o
- **agregue o modifique un endpoint** (ruta `@router.*` en `api/controller/*.py`), o
- **sume una nueva fuente de tasa** (plataforma), o cambie la firma/modelo de algo ya documentado.

## Checklist obligatorio (en el MISMO PR)

### 1. Método de servicio nuevo/modificado
- **Docstring** que describa propósito y, para lógica no trivial (scraping, ROC, promediado, persistencia, parseo), estilo Google con `Args:` / `Returns:` / `Raises:`.
- **Type hints veraces**: la anotación `-> tipo` debe coincidir con lo que realmente retorna (ojo con funciones que devuelven `{date, currencies}` en vez de `List[Currency]`).

### 2. Endpoint nuevo/modificado
Replica el patrón de los endpoints existentes de `dollar_controller.py` (ver `/bybit/averaged`, `/airtm` como referencia):
- En el decorador `@router.*`: `summary`, `description`, `response_model=BaseResponse[T]`, `status_code`, `response_description` y bloque `responses` con los códigos reales (`200`, y los de error aplicables `408`/`502`/`500`) usando `ErrorResponse`. (Ver también la regla `standard-response`.)
- **Docstring de una línea** en la función del endpoint, en el mismo tono que el resto (`"""Devuelve ..."""`).

### 3. Fuente de tasa nueva
Además de lo anterior, agrégala a **todas** las listas ilustrativas de fuentes que deben permanecer sincronizadas (abajo) y registra su nombre/logo en `Constants` + el mapeo de `serialize_with_image` (ver regla `constants-centralization`).

## Listas de fuentes que deben permanecer sincronizadas

Al sumar (o renombrar) una fuente, actualízala en **todas** estas menciones para que reflejen el contrato real:

- `APP_DESCRIPTION` — `api/utils/constants/constants.py` (la lista de fuentes en la bienvenida).
- `SOURCE_*_MSG` (comentario de fuentes) — `api/utils/constants/constants.py`.
- Docstring de `ExternalSourceError` — `api/core/errors/exceptions.py`.
- Comentario del handler global `external_source_error_handler` — `api/main.py`.
- Descripción del tag OpenAPI de tiempo real (`"Venezuela"`) — `api/utils/constants/tags_metadata.py`.

> **Distinguir doc de comportamiento.** Las menciones en `get_all_currencies` (endpoint agregado) y en `update-currencies` (persistencia) describen **lo que esos endpoints realmente hacen**. Solo agrega la fuente ahí si de verdad participa en el agregado o en la persistencia; si no (como Airtm, que solo tiene endpoint propio), **no** la añadas: esas descripciones seguirían siendo correctas sin ella.

## Verificación rápida

```bash
# a) Ningún endpoint del controller sin docstring
python -c "import ast; t=ast.parse(open('api/controller/dollar_controller.py').read()); \
print([n.name for n in ast.walk(t) if isinstance(n,(ast.AsyncFunctionDef,ast.FunctionDef)) \
and any(getattr(getattr(d,'func',None),'attr','') in ('get','post','put','delete') for d in n.decorator_list if isinstance(d,ast.Call)) \
and ast.get_docstring(n) is None] or 'todos documentados')"

# b) Toda operación visible en OpenAPI expone summary Y description
#    (levanta la app y revisa /openapi.json, como hizo DT-013)
```

Además: `pytest` debe seguir en verde (la documentación no cambia comportamiento).

## Excepción

Cambios puramente internos que no exponen superficie pública ni tocan servicios/controllers (p. ej. un helper privado de un script suelto) no requieren el bloque OpenAPI, pero **sí** un docstring si encapsulan lógica no obvia.
