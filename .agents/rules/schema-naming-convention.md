---
description: Convenciones de nombres para modelos (Schema) de Pydantic y modelos ORM (SQLAlchemy), basadas en el feature/endpoint donde se usan
---
# Convención de Nombres de Esquemas

FastAPI y Swagger dependen de los nombres de las clases para generar una documentación legible y ordenada. En este proyecto los schemas **no** se nombran por operación CRUD genérica (`Create`/`Update`/`Read`), sino **por el feature o endpoint donde se implementan**, más un sufijo que indica su rol. Así el schema dice de un vistazo a qué endpoint pertenece y qué papel cumple.

## Dos familias de modelos

Ambas viven bajo `api/models/`, pero son cosas distintas y se nombran distinto:

1. **Schemas de Pydantic** (`BaseModel`): validación de entrada y forma de la respuesta. Están en `api/models/schemas.py` (o, si son muy locales a un endpoint, definidos inline en su controller, como `HealthCheckResponse`).
2. **Modelos ORM de SQLAlchemy** (heredan de `Base`): representan tablas de la base de datos. Están en `api/models/bd_currency.py`.

## Convención para schemas de Pydantic

Formato general: **`<Feature><Rol>`**, donde `<Feature>` es el endpoint/fuente/dominio (`Bcv`, `AllCurrencies`, `UpdateCurrencies`, `HealthCheck`, `Currency`, `Error`…) y `<Rol>` es uno de estos sufijos:

| Sufijo | Rol | Ejemplos reales |
|---|---|---|
| `*Schema` | DTO reutilizable de una entidad; suele viajar dentro de otros payloads. | `CurrencySchema` |
| `*ResponseData` | El payload concreto que va en el campo `data` de `BaseResponse[T]` para **un endpoint específico**. | `BcvResponseData`, `AllCurrenciesResponseData`, `UpdateCurrenciesResponseData` |
| `*Response` | Un `response_model` completo por sí mismo (envelope propio, no va anidado). | `BaseResponse[T]`, `ErrorResponse`, `HealthCheckResponse` |

Reglas:
1. El **prefijo describe el feature/endpoint**, no una operación CRUD. Si el schema es el payload del endpoint "todas las monedas", se llama `AllCurrenciesResponseData`; si es el del endpoint de actualización, `UpdateCurrenciesResponseData`.
2. Usa `*ResponseData` cuando el schema es el `T` que se inserta dentro de `BaseResponse[T]` (ver `standard-response.md`), y `*Response` cuando es el `response_model` completo del endpoint.
3. Usa `*Schema` para un modelo de datos reutilizable que aparece dentro de varios payloads (como `CurrencySchema`, que se usa suelto y también dentro de `BcvResponseData` y `AllCurrenciesResponseData`).
4. Un schema muy acoplado a un solo endpoint puede definirse **inline en su controller** (ej. `HealthCheckResponse` en `health_controller.py`); si se reutiliza, muévelo a `schemas.py`.

### Ejemplo (patrón real del proyecto)

```python
from pydantic import BaseModel, Field
from typing import Optional, List, Generic, TypeVar

T = TypeVar("T")

# Envelope estándar (*Response): response_model completo.
class BaseResponse(BaseModel, Generic[T]):
    status: str
    message: str
    data: Optional[T] = None

# DTO reutilizable de una entidad (*Schema).
class CurrencySchema(BaseModel):
    code: str
    name: str
    platform: str
    value: float
    change: float

# Payload de un endpoint concreto (*ResponseData): va dentro de BaseResponse[T].
class BcvResponseData(BaseModel):
    date: Optional[str] = None
    currencies: List[CurrencySchema]

class AllCurrenciesResponseData(BaseModel):
    bcv: List[CurrencySchema]
    yadio: List[CurrencySchema]
    binance: List[CurrencySchema]
```

## Convención para modelos ORM (SQLAlchemy)

Los modelos que mapean tablas se nombran por la **entidad en singular, sin sufijo**, y heredan de `Base`:

```python
class Currency(Base):       # tabla "currencies"
    __tablename__ = "currencies"
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String, nullable=False, index=True)
    ...

class PlatformDate(Base):   # otra entidad/tabla del dominio
    ...
```

No mezcles el modelo ORM con su schema de Pydantic: `Currency` (tabla) y `CurrencySchema` (DTO de respuesta) son clases separadas y esa distinción de nombre (`*` vs `*Schema`) es intencional.

## Clases de dominio "planas"

Si necesitas una clase de dominio que **no** es ni Pydantic ni ORM (un objeto de trabajo interno), nómbrala por su fuente/feature sin sufijo de schema, como `BcvCurrency` (`api/models/bcv_currency.py`).

## Resumen

- **Nombra por feature/endpoint**, no por operación CRUD genérica.
- Pydantic: `<Feature>Schema` (DTO reutilizable), `<Feature>ResponseData` (payload dentro de `BaseResponse[T]`), `<Feature>Response` (response_model completo).
- ORM SQLAlchemy: entidad en singular sin sufijo (`Currency`, `PlatformDate`).
- Dominio plano: por su fuente/feature (`BcvCurrency`).
