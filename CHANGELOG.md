# Changelog

Todos los cambios notables de este proyecto se documentan en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/),
y el proyecto sigue [Semantic Versioning](https://semver.org/lang/es/).

## [1.1.1] - 2026-04-15

_The Professionalization Update. Detalle completo en [`docs/release/RELEASE_v1.1.1.md`](docs/release/RELEASE_v1.1.1.md)._

### Added
- Custom ReDoc Dark Theme basado en la paleta de colores de `themeV2.json`.
- Custom Swagger UI con CSS inyectado para mantener coherencia visual con la marca.
- Identidad visual: `logo_center.svg` y `favicon.ico` integrados en toda la UI de la API.
- Página raíz dinámica que actúa como portal de bienvenida con accesos directos.
- Health Check: endpoint `/health` (JSON) y `/health/ui` (visual) para monitoreo de uptime.
- Licencia MIT.
- Guías de contribución para colaboradores externos.

### Changed
- Modularización de controladores: `docs_controller.py` y `health_controller.py` para limpiar el punto de entrada de la app.
- Ajustes de configuración para despliegues fluidos en Vercel.
- `.gitignore` afinado para entornos virtuales y limpieza de archivos de sistema.

## [1.1.0] - 2026-02-03

### Added
- Seguimiento de cambios de moneda y gestión de fecha de plataforma (change tracking).
- Registro de reloj de ejecución para los guardados (save execution clock).
- Soporte inicial para nuevos activos bancarios.
- Favicon.

### Fixed
- Refuerzo de la búsqueda por vigencia de fecha (enforce date vigency).
- Dependencias faltantes añadidas (hotfix de requerimientos).

### Changed
- Actualización de imágenes y recursos.

## [1.0.0] - 2026-01-28

### Added
- Nueva arquitectura modular: cliente HTTP para requests, config manager para leer `.env`, constantes divididas por políticas de negocio y capa de helpers.
- Servicios de búsqueda de monedas y endpoints del servicio de dólar.
- Envoltorio de respuesta (response wrapper) estandarizado.
- Plantilla HTML raíz y renderizado con datos desde `.env`.
- Persistencia para guardar y obtener monedas guardadas.
- Modo `bcv/with-memory`: usar la moneda del BCV en memoria o volver a scrapearla.
- Dockerfile y comando de ejecución.
- Constantes de nombre y versión de la app; helpers de formato de fecha y valor.

### Changed
- Refactor del modelo y de la estructura de BD de monedas.
- Reubicación de constantes y helpers a su nueva ubicación.

## [0.5.0] - 2025-11-06

### Added
- Implementación inicial de la API DolarTracker con funcionalidades de tipo de cambio.
- Workflow programado de GitHub Actions para scraping diario mediante cron.
- Manejo de conexión a PostgreSQL (psycopg2) y lógica de recuperación de monedas.
- Clase `Helper` para gestión de zona horaria.
- Carga de variables de entorno al inicio (dotenv).

### Fixed
- Corrección de rutas de importación entre controladores y servicios.
- Manejo de errores en la importación del router.
- Simplificación de la lógica de comparación de fechas.

[1.1.1]: https://github.com/Teixeira49/bcv_tracker_backend/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/Teixeira49/bcv_tracker_backend/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/Teixeira49/bcv_tracker_backend/compare/v0.5.0...v1.0.0
[0.5.0]: https://github.com/Teixeira49/bcv_tracker_backend/releases/tag/v0.5.0
