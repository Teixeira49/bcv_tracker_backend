# [✨ Feat: DT-011] - Integrar Airtm como fuente de tasa USD/VES

# Descripción

Integra **Airtm** como nueva fuente de tasa de cambio, siguiendo el mismo patrón que las fuentes existentes (Yadio, Binance, Bybit). Airtm expone un JSON público y sin autenticación en `rates.airtm.io` con la forma `{"data": {"ves/usd": {"addValue": <compra>, "withdrawValue": <venta>}}}`, donde `addValue` es la tasa para agregar fondos (comprar USD pagando VES → **Buy**) y `withdrawValue` la de retirar (vender USD → VES → **Sell**).

Cambios concretos:

1. **config** (`config.py`): nueva variable de entorno `MARKET_DATA_PROVIDER_D_URL`, validada fail-fast en `Config.validate()`.
2. **endpoints** (`dollar_endpoints.py`): `PAR_MKT_D` + `getAirtmRates()` (el JSON se sirve en la raíz del host).
3. **services** (`dollar_services.py`): `getCurrenciesByAirtm` (serializado) y `get_raw_airtm_currencies` (crudo), con un helper de parseo compartido; registro del logo en `serialize_with_image`. Si el par `ves/usd` falta o viene incompleto se propaga `SourceEmptyError` (502), igual que el resto de fuentes.
4. **controller** (`dollar_controller.py`): nuevo endpoint `GET /api/v1/venezuela/airtm`.
5. **constants** (`constants.py`): `AIRTM_NAME` / `AIRTM_LOGO_URL` + línea en `APP_DESCRIPTION`.
6. **tests** (`test_airtm_rates.py`): respuesta OK (Buy/Sell), par ausente/incompleto → 502, y serialización con logo.
7. **conftest** (`conftest.py`): siembra `MARKET_DATA_PROVIDER_C_URL` y `_D_URL` para que la suite corra sin depender de un `.env` local (C faltaba desde la integración de Bybit; sin ello los tests que montan la app fallaban en un checkout limpio/worktree).

Issue de GitHub relacionado: `Closes #55`

### Nuevas variables de entorno

- `MARKET_DATA_PROVIDER_D_URL` — base del proveedor Airtm (valor público: `https://rates.airtm.io`).

> Nota: `.env.example` no se actualiza en esta PR porque ese archivo no existe en `development` (vive en otra rama en desarrollo, `chore/DT-010`). Al converger las ramas debe añadirse ahí la línea `MARKET_DATA_PROVIDER_D_URL=https://rates.airtm.io`.

## Tipo de cambio

- [x] ✨ Nueva funcionalidad (cambio no-breaking que agrega funcionalidad)
- [ ] 🛠️ Corrección de errores (cambio no-breaking que arregla un error)
- [ ] ❌ Cambio importante (arreglo o característica que haría que la funcionalidad existente no funcionara como se esperaba)
- [ ] 📝 Actualización de la documentación
- [ ] 🧹 Code refactoring (modificación de la estructura interna del código sin modificar las APIs)
- [ ] ✅ Build configuration change (modificación de los archivos para hacer deploy)
- [ ] 🗑️ Chore (actividades que no modifican la interacción con la app, por ejemplo, modificar el archivo de eslint)

## ¿Cómo se ha probado esto?

- [x] Suite completa de pytest en verde (28 passed) dentro del worktree.
- [x] Verificación end-to-end real contra `https://rates.airtm.io/`: la URL se compone correctamente y el servicio devuelve las 2 tasas (Buy/Sell) parseadas (ej. Buy ≈ 841.83 VES, Sell ≈ 799.47 VES), con `platform=Airtm` y logo.
- [x] Casos de borde cubiertos por tests: par `ves/usd` ausente, par vacío, falta `addValue` o `withdrawValue`, `data` nulo, respuesta vacía → todos propagan `SourceEmptyError` (502).

**Configuración de prueba**:

- `MARKET_DATA_PROVIDER_D_URL=https://rates.airtm.io`
- Resto de variables con URLs marcador (los tests mockean la red).

## Lista de Verificación

- [x] He agregado las nuevas dependencias en la descripción (no hay dependencias nuevas)
- [x] He agregado las nuevas variables de entorno (solo los nombres y rutas) a la descripción
- [x] Mi código sigue las pautas de estilo de este proyecto
- [x] He realizado una auto-revisión de mi código
- [x] He comentado mi código, particularmente en áreas difíciles de entender
- [ ] He realizado los cambios correspondientes a la documentación (ver nota sobre `.env.example`)
- [x] Mis cambios no generan nuevas advertencias
- [x] Mis cambios pasan el build y lint del proyecto localmente
- [x] He agregado pruebas que prueban que mi solución es efectiva o que mi función funciona
- [x] Las pruebas unitarias nuevas y existentes pasan localmente con mis cambios
