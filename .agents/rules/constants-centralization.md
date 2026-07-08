---
description: Prohíbe los valores "mágicos" en el código y obliga a centralizar constantes en api/utils/constants/. Aplica cada vez que se introduzca o modifique un literal reutilizable (números, strings, timeouts, flags, URLs, etiquetas de scraping).
---
# Centralización de Constantes

Para mantener el código legible, consistente y fácil de ajustar, **no se escriben valores "mágicos" directamente en el código**. Todo literal con significado de negocio o de configuración se declara como constante en `api/utils/constants/` y se referencia desde ahí. Esta regla formaliza la pauta de manejo de constantes descrita en `CONTRIBUTING.md`.

## Dónde vive cada constante

| Tipo de valor | Archivo | Clase / acceso |
|---|---|---|
| Configuración y valores de negocio (timeouts, nombres de plataforma, URLs de logos, flags, mensajes de estado, límites) | `api/utils/constants/constants.py` | `Constants` (se importa como `from api.utils.constants.constants import Constants as c`) |
| Clases/IDs de CSS y llaves para el scraping con BeautifulSoup | `api/utils/constants/scrapping_tags.py` | `ScrappingTags` (se importa como `... import ScrappingTags as tag`) |

## Reglas de Implementación

1. **Cero literales mágicos**: si un número, string, timeout, flag o URL tiene significado (no es un `0`/`1`/`""` trivial de control de flujo) y/o puede reutilizarse, declara una constante en lugar de incrustarlo.
2. **Un único punto de verdad**: si el mismo valor aparece en más de un lugar, debe existir una sola constante y todos los usos la referencian. No se duplica el literal.
3. **Nomenclatura**: `UPPER_SNAKE_CASE` como atributo de la clase correspondiente (ej. `HTTP_TIMEOUT`, `BCV_NAME`, `VERIFY`, `PAGE_LIMIT`).
4. **Sin `DEFAULT_*` embebidos en las clases de dominio/infraestructura**: los valores por defecto de parámetros (ej. el `timeout` de `HttpClient`) toman su valor de la constante centralizada, no de un atributo local de la clase ni de un literal en la firma.
5. **Alcance del cambio**: al tocar código que ya contiene un literal mágico relacionado con lo que estás modificando, aprovéchalo para extraerlo a la constante (regla del boy-scout), siempre que no desvíe el objetivo del PR.

## Ejemplo

**❌ Antes** — valor mágico y `DEFAULT_*` local:

```python
class HttpClient:
    DEFAULT_TIMEOUT = 10.0

    def __init__(self, timeout: float = DEFAULT_TIMEOUT):
        self._timeout = httpx.Timeout(timeout)
```

**✅ Después** — constante centralizada en `Constants`:

```python
# api/utils/constants/constants.py
class Constants:
    HTTP_TIMEOUT = 10.0
```

```python
# api/core/client/http_client.py
from api.utils.constants.constants import Constants as c

class HttpClient:
    def __init__(self, timeout: float = c.HTTP_TIMEOUT):
        self._timeout = httpx.Timeout(timeout)
```

## Excepciones

Esta regla no aplica a:

* Literales triviales de control de flujo sin significado de negocio (índices `0`/`1`, cadena vacía como acumulador, `None`).
* Valores locales de un solo uso dentro de una función cuyo significado ya es evidente por el contexto inmediato y no se reutilizan.
* Constantes que ya provienen de librerías estándar o del framework.
