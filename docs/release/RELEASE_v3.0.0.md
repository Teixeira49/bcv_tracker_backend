# Release Notes - v3.0.0 🚀
**DolarTracker Backend: The Contract & Performance Update**
*Fecha de lanzamiento: 26 de Julio de 2026*

---

## 💎 Visión General

La versión **3.0.0** es el primer release **breaking** desde *The Hardening &
Versioning Update*. Rediseña el contrato de entrada de los dos endpoints de
escritura/lectura masiva: la maraña de catorce flags booleanos de
`update-currencies` y `saved-currencies` se sustituye por un **Body estructurado
por mercado**, validado con Pydantic, que describe el **estado** de cada fuente
mediante una máquina de estados explícita.

Alrededor de ese cambio, el release consolida tres frentes más: **rendimiento**
(dos patrones N+1 eliminados y clientes HTTP con keep-alive compartidos a nivel
de app), **estructura** (routers que poseen la versión, listos para múltiples
países y versiones coexistiendo) e **infraestructura** (Docker funcional,
dependencias reproducibles, logging estructurado y un cron que refresca las nueve
fuentes con el contrato nuevo).

---

## ⚠️ Cambios que rompen compatibilidad

El único cambio breaking afecta a **dos endpoints**. El resto de la API
(`/bcv`, `/binance`, `/yadio`, `/okx`, `/airtm`, … y sus variantes) **no cambia**.

| | Antes (v2.1.1) | Ahora (v3.0.0) |
|---|---|---|
| `update-currencies` | `PUT` + query params | `PUT` + **Body** |
| `saved-currencies` | **`GET`** + query params | **`POST`** + **Body** |
| Selección de fuentes | 9 flags booleanos | `markets: {mercado: modo}` |
| Filtros | `fill_missing`, `enforce_bcv_dollar`, `enforce_yadio_dollar`, `enforce_em_own`, `enforce_em_average` | absorbidos por el **modo** de cada mercado |

### Guía de migración

**Antes:**
```http
GET /api/v1/venezuela/saved-currencies?bcv=true&enforce_bcv_dollar=true&binance=true
PUT /api/v1/venezuela/update-currencies?bcv=true&yadio=true&exchange_monitor=true
```

**Ahora:**
```http
POST /api/v1/venezuela/saved-currencies
Content-Type: application/json

{ "markets": { "bcv": "bd-solo-dolar", "binance": "bd-todas" } }
```
```http
PUT /api/v1/venezuela/update-currencies
Content-Type: application/json

{ "markets": { "bcv": "todas", "yadio": "todas", "exchange_monitor": "own+monitor" } }
```

**Equivalencias de los flags retirados:**

| Flag anterior | Equivalente en el Body |
|---|---|
| `bcv=true` (en `saved-currencies`) | `"bcv": "bd-todas"` |
| `bcv=true` (en `update-currencies`) | `"bcv": "todas"` |
| `enforce_bcv_dollar=true` | `"bcv": "bd-solo-dolar"` (o `"solo-dolar"` en vivo) |
| `enforce_yadio_dollar=true` | `"yadio": "bd-solo-dolar"` |
| `enforce_em_own=true` | `"exchange_monitor": "own"` |
| `enforce_em_average=true` | `"exchange_monitor": "own+monitor"` |
| `fill_missing=true` | mezclar modos `bd-*` y en vivo en el mismo Body |

Un mercado **no mencionado** en el Body equivale a `off`: no se consulta ni se
persiste. Y `update-currencies` **rechaza los modos `bd-*` con `422`**: no tiene
sentido "actualizar" leyendo de la base de datos.

---

## 🧩 El nuevo contrato: Body y máquina de estados (#71)

Cada mercado declara su **estado**, y el estado determina origen (vivo o BD) y
alcance (todas las divisas o solo el dólar) en una sola palabra:

| Modo | Significado | Aplica a |
|---|---|---|
| `off` | no se toca | todos |
| `solo-dolar` / `todas` | en vivo, USD o todas sus divisas | BCV, Yadio, Airtm, DolarAPI |
| `bd-solo-dolar` / `bd-todas` | desde BD, USD o todas | según mercado |
| `average` / `ambas` | en vivo, promedio `(buy+sell)/2` o ambos lados | Binance, Bybit, OKX, Bitget |
| `own` / `own+monitor` | valor propio, o valor propio + promedio | Exchange Monitor |

Las combinaciones admisibles se validan por mercado con Pydantic
(`ALLOWED_MODES`), devolviendo `422` con el listado de modos válidos cuando la
combinación no aplica — pedirle `average` al BCV es un error de contrato, no un
comportamiento silencioso. Agregar un mercado nuevo ya no requiere params
nuevos: basta su entrada en `MarketName` y su set de estados permitidos.

Diseño completo en [`docs/architecture/market-request.md`](../architecture/market-request.md).

---

## ⚡ Rendimiento

*   **N+1 eliminado en `calculate_live_changes` (#27)**: se ejecutaba una consulta
    por moneda para leer su valor previo y calcular el ROC. Ahora los valores se
    precargan con un único `SELECT` (doble `IN` sobre `code` y `platform`,
    portable entre SQLite y PostgreSQL) y el par exacto se resuelve en memoria.
    El número de queries es **constante**, independiente de la cantidad de monedas.
*   **N+1 eliminado en `save_currencies_to_db` (#48)**: el hermano del anterior, en
    el camino de escritura. Se precargan las filas existentes del lote en una sola
    consulta. Se cachean las **entidades ORM** —no solo el valor— para preservar la
    semántica del identity map cuando el lote trae varias monedas con el mismo
    `(code, platform)` (p. ej. Binance buy/sell).
*   **Lectura acotada en SQL (#46)**: `_query_latest_rows` devuelve la última fila
    por `(code, platform)` aplicando los filtros de plataforma y solo-dólar **en
    SQL**, no en Python. El resultado no se degrada aunque crezca el histórico (#14).
*   **Clientes HTTP compartidos con keep-alive (#50)**: cada llamada sin cliente
    explícito abría un `AsyncClient` efímero, pagando handshake TCP+TLS por
    petición. Ahora el `lifespan` crea y reutiliza clientes a nivel de app. Se
    mantienen **dos** clientes aislados (`verify=True` y `verify=False`) para que
    la desactivación de TLS del scraping del BCV **no se filtre** al resto de
    fuentes. Exchange Monitor conserva su cliente efímero a propósito: su flujo
    CSRF depende de la cookie `PHPSESSID` por request.
*   **Micro-optimizaciones en el path caliente (#49)**: `createCurrency` deja de
    instanciar `Helper()` dos veces por moneda y toma una sola lectura de hora para
    ambas fechas; el mapa de imágenes de plataforma pasa a constante de clase en
    lugar de reconstruirse en cada serialización.

---

## 🏗️ Evolución de la arquitectura

**Versionado: el router posee la versión (#52).** El versionado era un detalle de
routing (`prefix=API_V1_STR` al montar el controller): funcionaba con una versión,
pero no expresaba la coexistencia de varias ni dónde se agregan controllers por
país. Se evaluaron tres opciones con matriz de decisión —eficiencia, efectividad,
escalabilidad, mantenibilidad, complejidad y adaptación a futuros países— y ganó
la **Opción A** (8.8/10).

| | Antes | Ahora |
|---|---|---|
| Dueño de la versión | `main.py` al montar el controller | `api/router/v1.py` |
| Agregar un país | tocar `main.py` | incluir su router en `v1.py` |
| Agregar una v2 | replantear el montaje | `api/router/v2.py` análogo, sin tocar v1 |
| Nombre del controller | `dollar_controller.py` | `venezuela_controller.py` |

Las rutas públicas **no cambian**: `/api/v1/venezuela/...`. Decisión documentada
en [`docs/architecture/api-versioning.md`](../architecture/api-versioning.md).

---

## 🐳 Infraestructura y build

*   **Docker funcional de verdad (#25)**: el README anunciaba soporte para Docker
    pero `docker-compose.yml` estaba vacío y no existía `Dockerfile`. Se entrega la
    imagen (`python:3.12-slim`, usuario **no-root**, `uvicorn` en el 8000), el
    `.dockerignore` que mantiene `venv/`, `.git/` y los secretos fuera del contexto
    de build, y un compose con API + PostgreSQL que espera el `healthcheck` de la BD.
*   **Dependencias reproducibles (#24)**: todo `requirements.txt` pinneado con `==`
    a la versión verificada. Se eliminan dos paquetes erróneos: `asyncio` (es
    stdlib desde Python 3.4; instalarlo desde PyPI puede sombrear el módulo
    estándar) y `dotenv` (distribución equivocada; la correcta, `python-dotenv`, ya
    estaba). `requirements-dev.txt` también queda pinneado.

---

## 🪵 Observabilidad

*   **Logging estructurado (#26)**: el service registraba errores con `print()` —sin
    nivel, timestamp ni contexto— y `main.py` volcaba tracebacks con
    `traceback.print_exc()`. Ahora hay un logger central (`get_logger()` con
    namespace `dolartracker.<módulo>`, `configure_logging()` idempotente), nivel
    configurable con la variable **opcional** `LOG_LEVEL` (INFO por defecto, no
    requerida para arrancar) y `logger.exception()` preservando el traceback completo.
*   **Guardrail contra la regresión**: la regla `logging-convention.md` más un test
    con check AST que **falla si aparece `print(` en `api/`**, corriendo en local y en CI.

---

## 🤖 Automatización

*   **El cron refresca las nueve fuentes (#72)**: solo actualizaba `bcv`, `yadio` y
    `binance`, con query params. Ahora envía el Body por mercado: P2P cripto en
    `ambas`, fiat y agregadores en `todas`, Exchange Monitor en `own+monitor`.
*   **Cadencia documentada**: seis corridas diarias (`04:00, 07:00, 11:00, 14:45,
    18:15, 23:00` UTC); el **BCV** se incluye solo en la de las `04:00 UTC`, que es
    la medianoche en Venezuela (UTC-4). Se añade `workflow_dispatch` para corridas
    manuales.
*   **Fallo visible**: cualquier respuesta no-2xx imprime el cuerpo y hace `exit 1`,
    dejando el job en rojo en lugar de fallar en silencio.
*   **Listo para autenticación (#13)**: si el secreto `UPDATE_API_KEY` está definido
    se envía como `Authorization: Bearer`; si no, la llamada va sin cabecera.
*   **Decisión GitHub Actions vs Vercel Cron** documentada en
    [`docs/architecture/scheduled-scrape.md`](../architecture/scheduled-scrape.md):
    se mantiene GitHub Actions por ser neutral al hosting, gratuito para este uso y
    auditable desde el repo.

---

## 🛠️ Correcciones

*   **Forma de respuesta unificada en `update-currencies` (#30)**: el camino de éxito
    devolvía `updated_count` y el early-return sin datos `updated_currencies`. Solo
    coincidían en el JSON final gracias a `populate_by_name` + `response_model`
    (frágil). Ahora ambos caminos devuelven `{message, updated_count}`.
*   **Import obsoleto tras el rename del controller**: mergear #50 y #52 produjo un
    merge semántico roto —sin conflicto textual, porque tocaban bloques distintos de
    `main.py`— que dejaba referencias al módulo con su nombre viejo. El `lifespan`
    lanzaba `ModuleNotFoundError` (capturado, cayendo a clientes efímeros y perdiendo
    el keep-alive) y la suite quedaba en rojo en `development`.
*   **Config de Pydantic v1 migrada a v2 (#29)**: `class Config: populate_by_name` era
    estilo deprecado; pasa a `model_config = ConfigDict(...)`. Sin warnings de
    deprecación al importar o arrancar.

---

## ✅ Verificación

Suite completa en verde: **132 tests**, incluyendo los nuevos que cuentan
sentencias SELECT para blindar ambos N+1, los que cubren la máquina de estados y
los modos del Body, y el guardrail AST contra `print()`.

---

## 🚀 Próximos Pasos
*   Autenticación para los endpoints de escritura (#13).
*   Caché en memoria (TTL) para las tasas en vivo.
*   Persistencia de histórico real (serie temporal).
*   Segundo país sobre la estructura de routers por versión.

---
*DolarTracker - Monitorizando la economía con precisión y elegancia.*
