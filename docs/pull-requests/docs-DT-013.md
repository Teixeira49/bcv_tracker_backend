# [📝 Doc: DT-013] - Documentar endpoints y servicios (docstrings + OpenAPI)

# Descripción

Uniforma la documentación del código y de la documentación interactiva (Swagger/ReDoc), **sin cambios de comportamiento**. Completa las lagunas de docstrings en la capa de servicios y añade docstrings a las funciones de endpoint, dejando el contrato documentado alineado con las fuentes reales.

Cambios concretos:

1. **Services**:
   - `dollar_services.py`: docstrings en todos los métodos públicos que faltaban (`getDollarValueByBCV`, `getCurrenciesByBCV`, `getCurrenciesByYadio`, `getDollarByYadio`, `getCurrenciesByBinance`, `getCurrenciesByBybit`, `getSavedCurrencies`, `createCurrency`) — propósito, parámetros y retorno.
   - `bd_service.py`: docstrings en `save_currencies_to_db`, `save_platform_date` y `get_platform_date`.
2. **Capa transversal** (documentación en todo el código): docstrings en los métodos de `HttpClient`, en `Helper` (`getZoneTime`, `formatCuValue`, `validateDate`) y en `api_response`.
3. **Endpoints**: docstrings en las funciones de los controllers (`dollar_controller`, `docs_controller`, `health_controller`) y en el `root`/handlers de `main.py`. Todos los endpoints visibles en OpenAPI ya exponen `summary` + `description`.
4. **Precisión documental**: se actualizan las menciones ilustrativas de fuentes que aún decían solo "BCV, Yadio, Binance" (en `main.py`, `exceptions.py`, `constants.py`) para incluir **Bybit** y **Exchange Monitor**, reflejando el contrato real. `APP_DESCRIPTION` ya lista las 5 fuentes de forma clara y completa.

**Nuevas dependencias:** ninguna. **Nuevas variables de entorno:** ninguna.

Issue de GitHub relacionado: Closes #4

## Tipo de cambio

- [ ] ✨ Nueva funcionalidad (cambio no-breaking que agrega funcionalidad)
- [ ] 🛠️ Corrección de errores (cambio no-breaking que arregla un error)
- [ ] ❌ Cambio importante
- [x] 📝 Actualización de la documentación
- [ ] 🧹 Code refactoring
- [ ] ✅ Build configuration change
- [ ] 🗑️ Chore

## ¿Cómo se ha probado esto?

- [x] **Suite completa** (`pytest`): 29 pruebas en verde (sin cambios de comportamiento).
- [x] **Cobertura de docstrings** (chequeo con `ast`): todos los métodos públicos de `dollar_services.py` y `bd_service.py` están documentados.
- [x] **App real** (`uvicorn`): `/docs`, `/redoc`, `/openapi.json` y `/health` responden 200; las 14 operaciones visibles en OpenAPI exponen `summary` **y** `description` (verificado sobre `openapi.json`).

**Configuración de prueba**:

- Python 3.10, venv con `requirements.txt` + `requirements-dev.txt`.

## Lista de Verificación

- [x] He agregado las nuevas dependencias en la descripción (ninguna)
- [x] He agregado las nuevas variables de entorno a la descripción (ninguna)
- [x] Mi código sigue las pautas de estilo de este proyecto
- [x] He realizado una auto-revisión de mi código
- [x] He comentado mi código, particularmente en áreas difíciles de entender
- [x] He realizado los cambios correspondientes a la documentación
- [x] Mis cambios no generan nuevas advertencias
- [x] Mis cambios pasan el build y lint del proyecto localmente
- [x] He agregado pruebas que prueban que mi solución es efectiva (N/A: solo docs; cubierto por la suite existente y el chequeo de OpenAPI)
- [x] Las pruebas unitarias nuevas y existentes pasan localmente con mis cambios
