# [✨ Feat: DT-012] - Exchange Monitor como fuente de tasa (scraping)

# Descripción

Añade **Exchange Monitor** como nueva fuente de tasas del dólar en Venezuela, reutilizando la estructura de las fuentes existentes.

Exchange Monitor no expone API pública ni sirve las tasas en el HTML estático (los contenedores `rate-container` llegan vacíos y se rellenan por JavaScript). La integración se resuelve con un **scraping híbrido** fiel al espíritu del patrón de BCV:

1. **GET** a la página `/dolar-venezuela`: entrega la cookie de sesión (`PHPSESSID`) y, en un `<meta name="csrf-token">`, el token CSRF, que se extrae **con BeautifulSoup** usando selectores centralizados en `ScrappingTags`.
2. **POST** al endpoint de datos JSON (`/data/rates/ve`) con ese token (`X-CSRF-Token`), reutilizando el **mismo** `HttpClient`/`httpx.AsyncClient` para conservar la cookie, más `Referer`/`Origin` (el backend responde 403 sin ellos). Todo dentro de `source_guard` para degradar con gracia.

Cambios concretos:

1. **Config** (`config.py`): nueva variable de entorno `MARKET_DATA_PROVIDER_D_URL`, validada al arrancar (fail-fast).
2. **DollarEndpoints**: URL de la página, endpoint de datos JSON y `Origin` de Exchange Monitor.
3. **Constants / ScrappingTags**: nombre y logo de la plataforma, claves del payload JSON, ids del sitio (`ve-em`, `ve-average`) y el selector del `<meta>` CSRF. Actualización de `APP_DESCRIPTION`.
4. **DollarService**:
   - `getCurrenciesByExchangeMonitor` (en vivo): valor propio + promedio estimado + **todos los mercados** que reporta el sitio.
   - `get_raw_exchange_monitor_currencies` (persistencia): guarda **solo** el valor propio (EM) y el promedio estimado.
   - Logo de la plataforma en `serialize_with_image`.
5. **Controller**: nuevo endpoint `GET /venezuela/exchange-monitor` y cableado de Exchange Monitor en el agregado (`GET /venezuela`), `update-currencies` y `saved-currencies`.
6. **Schemas / OpenAPI**: campo `exchange_monitor` en `AllCurrenciesResponseData` y mención en los tags/descripciones.
7. **Tests**: nueva suite `tests/test_exchange_monitor.py`.

**Nuevas variables de entorno** (solo nombre): `MARKET_DATA_PROVIDER_D_URL` (URL base de Exchange Monitor, ej. `https://exchangemonitor.net`).

Issue de GitHub relacionado: Closes #3

## Tipo de cambio

- [x] ✨ Nueva funcionalidad (cambio no-breaking que agrega funcionalidad)
- [ ] 🛠️ Corrección de errores (cambio no-breaking que arregla un error)
- [ ] ❌ Cambio importante (arreglo o característica que haría que la funcionalidad existente no funcionara como se esperaba)
- [ ] 📝 Actualización de la documentación
- [ ] 🧹 Code refactoring (modificación de la estructura interna del código sin modificar las APIs)
- [ ] ✅ Build configuration change (modificación de los archivos para hacer deploy)
- [ ] 🗑️ Chore (actividades que no modifican la interacción con la app)

## ¿Cómo se ha probado esto?

- [x] **Suite completa** (`pytest`): 29 pruebas en verde, incluyendo la nueva suite de Exchange Monitor (flujo CSRF+JSON, alcance de persistencia, y errores tipados 502 ante respuesta vacía o token ausente).
- [x] **Verificación en vivo** contra `exchangemonitor.net`: `getCurrenciesByExchangeMonitor` devuelve los 19 mercados (valor propio + promedio + resto) y `get_raw_exchange_monitor_currencies` solo el valor propio + promedio.
- [x] **App real** (`uvicorn`): `GET /api/v1/venezuela/exchange-monitor` responde con el envelope estándar; `GET /api/v1/venezuela` incluye la clave `exchange_monitor`; `openapi.json` refleja el nuevo path y el campo del esquema.

**Configuración de prueba**:

- Python 3.10, entorno virtual con `requirements.txt` + `requirements-dev.txt`.
- Variable `MARKET_DATA_PROVIDER_D_URL=https://exchangemonitor.net` en `.env`.

## Lista de Verificación

- [x] He agregado las nuevas dependencias en la descripción (no hay dependencias nuevas)
- [x] He agregado las nuevas variables de entorno (solo los nombres y rutas) a la descripción
- [x] Mi código sigue las pautas de estilo de este proyecto
- [x] He realizado una auto-revisión de mi código
- [x] He comentado mi código, particularmente en áreas difíciles de entender
- [x] He realizado los cambios correspondientes a la documentación (README + OpenAPI)
- [x] Mis cambios no generan nuevas advertencias
- [x] Mis cambios pasan el build y lint del proyecto localmente
- [x] He agregado pruebas que prueban que mi solución es efectiva
- [x] Las pruebas unitarias nuevas y existentes pasan localmente con mis cambios

> Nota: `.env.example` no existe aún en `development` (vive en la rama `chore/DT-010`); cuando esa rama se integre habrá que añadir allí `MARKET_DATA_PROVIDER_D_URL`.
