# Design tokens — DolarTracker

Fuente de verdad del **branding** del proyecto: paleta, tipografía, espaciado,
radios y estilos de componentes. Pensado para que cualquier superficie (docs de
la API, front) use un branding fijo y consistente.

## Archivos

- [`themeV2.json`](themeV2.json) — tokens de diseño (Deep Navy / Premium Dark Mode).

## Consumidores

- **Backend (OpenAPI):** los temas dark de Swagger y ReDoc derivan de esta
  paleta — ver `api/openapi/redoc_theme.py` y `api/openapi/swagger_theme.py`.
  > ⚠️ Hoy los valores están **transcritos a mano** en esos módulos, no se leen
  > de este JSON en runtime. Si cambias un token aquí, actualiza también esos
  > archivos (o migra el theming a leer este JSON).
- **Frontend:** referencia de branding para las pantallas (incluido desarrollo).
