---
description: Obliga a que toda implementación futura (una nueva fuente/mercado o un endpoint nuevo/modificado) incluya sus propios tests en el MISMO PR, para que la cobertura no se degrade respecto a la suite existente. Aplica cada vez que se agregue o modifique un endpoint o una fuente de tasa.
---
# Cobertura de Tests Obligatoria

El core del proyecto es scraping/consumo frágil de fuentes externas (HTML del BCV, JSONs de terceros P2P). La suite de tests (`tests/`) es la mayor red de seguridad contra regresiones. Esta regla evita que esa red se desactualice: **todo lo nuevo nace con sus tests**, en el mismo cambio, igual que el resto de la suite (creada/consolidada en DT-022, issue #20).

El riesgo concreto que evita: agregar una fuente o un endpoint **sin** tests, de modo que un cambio posterior en el parseo o en el proveedor rompa la producción sin que nada lo detecte.

## Cuándo aplica

Cada vez que un cambio:
- **agregue o modifique un endpoint** (`@router.*` en `api/controller/*.py`), o
- **sume o modifique una fuente de tasa** (plataforma) o su parseo/mapeo, o
- **cambie la lógica de un método público** del service que transforme datos externos (parseo HTML, mapeo JSON, promediado, ROC, persistencia).

Cambios puramente internos que no tocan superficie pública ni parseo (p. ej. un rename interno) no requieren tests nuevos, pero **no deben romper** los existentes.

## Checklist obligatorio (en el MISMO PR)

### 1. Fuente de tasa nueva o modificada
Replica el patrón de los tests de fuentes existentes (`tests/test_airtm_rates.py`, `test_bcv_parsing.py`, `test_yadio_binance_mapping.py`, `test_bybit_offers.py`, ...):
- **Mapeo/parseo feliz**: dado un payload representativo (JSON de la API, o un **fixture HTML grabado** en `tests/fixtures/` para scraping), la fuente produce los `Currency`/dicts esperados (código, nombre, valor, plataforma, logo).
- **Caso sin datos / degradación**: la fuente vacía o incompleta propaga el error tipado correcto (`SourceEmptyError`/`SourceUnavailableError` → 502) en vez de reventar.
- Si la fuente promedia (`average_by_asset`) o persiste, cúbrelo también.

### 2. Endpoint nuevo o modificado
- Un test que ejerza el endpoint (con `TestClient`), afirmando el **código HTTP** y la **forma de la respuesta** (envelope `BaseResponse` + `data`), mockeando la capa de servicio o la red.
- Los **casos de error** relevantes (timeout → 408, fuente caída/vacía → 502, validación → 400) con el envelope de error uniforme (ver `tests/test_error_handling.py`).

### 3. Capa HTTP / parseo transversal
- Si tocas `HttpClient` o el parseo compartido, usa `httpx.MockTransport` para simular respuestas (éxito, timeout, no-2xx, cuerpo vacío) — ver `tests/test_http_client_transport.py`.

## Verificación

- **La suite debe quedar en verde**: `pytest` sin fallos, localmente y en CI.
- **CI obligatorio**: el workflow `.github/workflows/tests.yml` corre `pytest` en **cada Pull Request** a `development`/`main`. Un PR con tests en rojo no se mergea.
- No reduzcas la cobertura existente: no borres ni "skipees" tests para que pase el build.

## Regla de oro

Si agregas o cambias una fuente o un endpoint y **no** agregas sus tests en el mismo PR, el cambio está incompleto.
