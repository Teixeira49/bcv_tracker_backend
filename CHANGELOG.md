# Changelog

Todos los cambios notables de este proyecto se documentan en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/),
y el proyecto sigue [Semantic Versioning](https://semver.org/lang/es/).

## [2.0.0] - 2026-07-08

_The Hardening & Versioning Update. Detalle completo en [`docs/release/RELEASE_v2.0.0.md`](docs/release/RELEASE_v2.0.0.md)._

### Added
- Versionado de los endpoints de negocio bajo el prefijo `/api/v1` (DT-008).
- Sobre de error uniforme con códigos tipados para todas las respuestas de error de la API (DT-007).
- Validación de variables de entorno requeridas al arranque, con fallo temprano y claro (DT-004).
- Proceso formal de CHANGELOG y versionado SemVer (DT-002).
- Versionado del tooling agéntico del repo: skills, rules y roles (DT-001).
- Control de despliegues en Vercel (allowlist `preview`/`main`) y flujo de promoción staged.
- Pruebas: caso de respuesta P2P vacía de Binance (DT-006) y sobre de error uniforme (DT-007).

### Changed
- **BREAKING**: los endpoints de negocio se movieron bajo `/api/v1`; los consumidores deben actualizar sus URLs (DT-008).
- `HttpClient` migrado a `httpx` asíncrono real; timeout HTTP extraído a `Constants` (DT-003).

### Fixed
- El scraper lanza errores tipados ante fallo de la fuente en vez de devolver una lista vacía con `200` (DT-005).
- Evitado `ZeroDivisionError` al promediar ofertas de Binance P2P validándolas antes (DT-006).

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

[2.0.0]: https://github.com/Teixeira49/bcv_tracker_backend/compare/v1.1.1...v2.0.0
[1.1.1]: https://github.com/Teixeira49/bcv_tracker_backend/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/Teixeira49/bcv_tracker_backend/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/Teixeira49/bcv_tracker_backend/compare/v0.5.0...v1.0.0
[0.5.0]: https://github.com/Teixeira49/bcv_tracker_backend/releases/tag/v0.5.0
