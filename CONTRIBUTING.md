# Guía de Contribución - BCV Tracker Backend 🤝

¡Gracias por tu interés en contribuir a **BCV Tracker**! Este documento detalla las reglas de implementación, la estructura arquitectónica y el flujo de trabajo para mantener el proyecto limpio, escalable y eficiente.

---

## 🏛️ Guía de Arquitectura

El proyecto utiliza una arquitectura basada en capas (Controller-Service-Model) para separar responsabilidades. Por favor, sigue este esquema al agregar nuevas funcionalidades:

### 1. Controllers (`api/controller/`)
- **Responsabilidad**: Definir las rutas (endpoints), recibir parámetros y devolver respuestas.
- **Regla**: **Cero lógica de negocio**. Los controladores solo deben llamar a los métodos correspondientes en la capa de Service.
- **Respuesta**: Siempre utiliza el helper `api_response` para mantener un formato de JSON consistente.

### 2. Services (`api/services/`)
- **Responsabilidad**: Contener toda la lógica central (scraping con BeautifulSoup, integración con APIs externas, cálculos de promedios, interacción con la base de datos).
- **Regla**: Utiliza `async` y `await` para todas las operaciones de I/O (peticiones de red o base de datos).

### 3. Models (`api/models/`)
- **Responsabilidad**: Definir la estructura de los datos.
  - Modelos de **SQLAlchemy** para la base de datos.
  - Esquemas de **Pydantic** para la validación de entrada/salida (si aplica).

### 4. Core & Utils (`api/core/`, `api/utils/`)
- **Core**: Contiene clientes base (como `HttpClient`) y wrappers de respuesta.
- **Utils**: Carpeta para constantes, etiquetas de scraping (`scrapping_tags.py`) y funciones auxiliares.

---

## 🛠️ Reglas de Implementación

Para mantener la calidad del código, sigue estas reglas:

1. **Async por defecto**: Todas las operaciones que involucren peticiones externas (scraping, APIs) o base de datos deben ser asíncronas.
2. **Inyección de Dependencias**: Si necesitas un servicio dentro de un controlador, instáncialo al inicio del archivo o usa el sistema de dependencias de FastAPI.
3. **Manejo de Constantes**: No escribas strings "mágicos" en el código. Agrégalos a `api/utils/constants/constants.py` o al archivo correspondiente.
4. **Scraping Limpio**: Si vas a añadir una nueva fuente de scraping, añade las clases/IDs de CSS a `api/utils/constants/scrapping_tags.py`.
5. **Base de Datos**: Cualquier cambio en los modelos de base de datos requiere una nueva migración de Alembic (`alembic revision --autogenerate`).
6. **Formateo**: Sigue los estándares de **PEP 8**. Se recomienda el uso de `black` o `autopep8`.

---

## 🔄 Flujo de Trabajo (Workflow)

1. **Explora el código**: Familiarízate con `api/services/dollar_services.py`, ya que es el núcleo del proyecto.
2. **Crea una rama**:
   ```bash
   git checkout -b feature/nombre-de-tu-mejora
   ```
3. **Instala dependencias**: Asegúrate de tener el entorno virtual activo y haber ejecutado `pip install -r requirements.txt`.
4. **Implementa**: Sigue las guías de arquitectura mencionadas arriba.
5. **Prueba localmente**: Ejecuta el servidor con `uvicorn api.main:app --reload` y verifica tus cambios en Swagger UI (`/docs`).
6. **Pull Request**: Sube tus cambios a tu fork y abre un PR describiendo detalladamente qué has añadido o corregido.

---

## 🏷️ Versionado y Changelog

El proyecto sigue **[Semantic Versioning](https://semver.org/lang/es/)** (`MAJOR.MINOR.PATCH`, con tags `vX.Y.Z`) y mantiene un historial formal en [`CHANGELOG.md`](CHANGELOG.md) con el formato **[Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/)**.

### Cómo elegir el incremento (SemVer)

| Cambio predominante | Parte que sube | Ejemplo |
|---|---|---|
| Breaking change (`!` o footer `BREAKING CHANGE:`) | **MAJOR** | `v1.1.1` → `v2.0.0` |
| `feat` (nueva funcionalidad no-breaking) | **MINOR** | `v1.1.1` → `v1.2.0` |
| `fix`, `perf`, `refactor`, `docs`, `build`, `chore`… | **PATCH** | `v1.1.1` → `v1.1.2` |

El `type` predominante de tus commits (ver arriba) determina el incremento.

### Proceso para actualizar el changelog en cada release

El changelog **no se edita a mano en cada commit**: se actualiza al **lanzar una versión**, a partir de un **PR ya aprobado y mergeado**. Por cada release:

1. Se determina la versión nueva según la tabla SemVer de arriba.
2. Se escribe la nota de release detallada en `docs/release/RELEASE_v<X.Y.Z>.md`.
3. Se agrega una entrada **concisa** al tope de `CHANGELOG.md` (orden descendente, la más reciente primero) con la fecha de merge y solo las subsecciones que apliquen (`Added`, `Changed`, `Fixed`, `Removed`, `Deprecated`, `Security`).
4. Se mantienen los enlaces de comparación por versión al final del archivo (`[X.Y.Z]: .../compare/vA.B.C...vX.Y.Z`).
5. Se crea el **GitHub Release** con el tag `vX.Y.Z` sobre `main`.

El detalle completo de este flujo (con los gates de confirmación) vive en la convención del repositorio [`.agents/rules/release-versioning.md`](.agents/rules/release-versioning.md). El `CHANGELOG.md` es el resumen navegable; la nota en `docs/release/` es el documento extenso, y ambos deben ser consistentes con lo que el PR realmente cambió.

---

## 🚀 Nuevas Fuentes de Datos

Si deseas agregar un nuevo monitor de divisas:
1. Añade los endpoints necesarios en `DollarEndpoints`.
2. Implementa el método de extracción en `DollarService`.
3. Si requiere persistencia, verifica que el modelo `Currency` sea compatible o actualízalo.
4. Registra el nuevo endpoint en `DollarController`.

---

## 🤖 Tooling Agéntico (`.agents/` y `.claude/`)

Este repositorio versiona un conjunto de **convenciones y capacidades para asistentes de IA** (Claude Code y compatibles), de forma que todo el equipo desarrolle con las mismas reglas y atajos sin configuración adicional. Al clonar el repo ya vienen incluidos.

### Estructura de `.agents/`

```
.agents/
├── rules/    # Convenciones obligatorias del repositorio
├── roles/    # Personas/expertos especializados para tareas concretas
└── skills/   # Capacidades instalables (guías + scripts + plantillas)
```

#### `rules/` — Convenciones del repositorio
Reglas que el asistente debe respetar en todo el flujo `issue → rama → commits → PR → release`:

| Regla | Para qué sirve |
|---|---|
| `branch-naming.md` | Nomenclatura de ramas (`<tipo>/DT-<núm>`) y vínculo con el issue de GitHub |
| `commit-convention.md` | Conventional Commits + gitmoji (estilo extensión *vivaxy*) |
| `issue-convention.md` | Formato de issues (título con gitmoji + User Story + criterios) |
| `pull-request.md` | Flujo, título y descripción de las PR (lee `.claude/pr-config.json`) |
| `release-versioning.md` | SemVer, GitHub Releases y mantenimiento del `CHANGELOG.md` |
| `standard-response.md` | Envelope de respuesta JSON consistente de la API |
| `constants-centralization.md` | Prohíbe valores "mágicos"; centraliza constantes en `api/utils/constants/` |
| `pagination-enforcement.md` | Uso obligatorio de paginación en endpoints de listado |
| `schema-naming-convention.md` | Convención de nombres del esquema de base de datos |
| `database-schema-sync.md` | Sincronización entre modelos y esquema documentado |
| `documentation-convention.md` | Todo método/endpoint/fuente nuevo nace documentado igual que el resto (docstring, OpenAPI y listas de fuentes sincronizadas) |

#### `roles/` — Expertos especializados
Personas que orientan al asistente según el tipo de tarea:

- `backend_architect.md` — arquitectura en capas (FastAPI), envelope y patrones async.
- `database_specialist.md` — capa de persistencia (SQLAlchemy + PostgreSQL), upsert y sesiones.
- `domain_guardian.md` — invariantes del dominio cambiario (tasas, plataformas, Buy/Sell).
- `performance_optimizer.md` — concurrencia async real y detección de código bloqueante.
- `security_sentinel.md` — seguridad de la API pública (endpoint de escritura, secretos, scraping).
- `documentation_agent.md` — OpenAPI/Swagger/ReDoc, docstrings y ejemplos de Pydantic.

#### `skills/` — Capacidades instalables
Skills traídas del ecosistema abierto (FastAPI, scraping con BeautifulSoup, paginación, diseño de APIs, Neon, cron, etc.). Se gestionan con el CLI `npx skills` y su procedencia queda fijada en **`skills-lock.json`** (raíz del repo), que registra el `source`, `skillPath` y un `hash` por skill para reproducibilidad.

```bash
npx skills find <query>     # buscar skills en el ecosistema
npx skills add <package>    # instalar una skill
npx skills check            # ver actualizaciones disponibles
npx skills update           # actualizar las skills instaladas
```

### Configuración: `.claude/pr-config.json`
Config compartida que las reglas leen para operar de forma consistente:

- `branchProjectCode`: iniciales del proyecto para el ID de rama (`DT`).
- `baseBranch` / `productionBranch`: `development` / `main`.
- `triggerMode`: nivel de autonomía para subir PR/releases (`manual` | `ask` | `auto`).
- `draftsDir`: carpeta de borradores de PR (`docs/pull-requests/`).
- `reviewers`: reviewers candidatos del equipo.

### Qué se versiona y qué se ignora
- ✅ **Se versiona**: `.agents/` (rules, roles, skills), `.claude/pr-config.json` y `skills-lock.json`.
- 🚫 **Se ignora** (ver `.gitignore`): config personal/local del asistente (`.claude/settings.local.json`, `.claude/*.local.json`, `.mcp.local.json`), variables de entorno (`.env`) y cualquier secreto o artefacto local. **Nunca** subas credenciales dentro de `.claude/` o `.agents/`.

### Cómo usarlas
1. Clona el repo: las reglas, roles y skills ya están disponibles, sin setup extra.
2. Usa un asistente compatible (ej. Claude Code) desde la raíz del proyecto; detectará automáticamente `.agents/` y `.claude/pr-config.json`.
3. Al crear issues, ramas, commits, PR o releases, el asistente aplicará las reglas de `.agents/rules/`.
4. Para tareas específicas, invoca el rol adecuado de `.agents/roles/`.
5. Para añadir o actualizar skills, usa `npx skills` y **commitea** los cambios en `.agents/skills/` junto con `skills-lock.json`.

---

¡Feliz codificación! Si tienes dudas, abre un **Issue** para discutir tu propuesta antes de empezar.
