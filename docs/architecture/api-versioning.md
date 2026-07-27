# Arquitectura de versionado de la API

> Decisión de diseño para el issue #52 (continuación de #42). Define cómo el
> backend versiona su contrato y cómo escala a múltiples controllers por país.

## Contexto

En #42 se introdujo el versionado por path montando el router de negocio con
`prefix=Constants.API_V1_STR` en `api/main.py`. Eso resolvía el *naming* de la
versión actual, pero era un **detalle de routing**, no una separación de
contrato: funcionaba mientras solo existiera `v1`, pero no expresaba dónde
coexisten dos versiones vivas ni dónde se agregan varios controllers (por país).

El versionado y el país son **dos dimensiones ortogonales** (versión × país):

- **País** → se resuelve con controllers/sub-routers de país.
- **Versión** → la debe **poseer** un router/paquete que ensambla esos controllers.

## Opciones evaluadas

- **A — El router posee la versión; controllers planos por país.**
  `api/router/v1.py` arma el `APIRouter` de v1 incluyendo los controllers
  (`venezuela_controller`, ...). v2 sería `api/router/v2.py` que reusa lo válido
  y solo cambia lo que rompe (**bump parcial**). Servicios y modelos compartidos.
- **B — Carpeta por versión** (`api/controller/v1/`, `v2/`): copia completa del
  set de controllers por versión. Aislamiento total, pero duplica la capa de
  contrato desde el día 1.
- **C — Sub-aplicaciones montadas** (`app.mount("/api/v1", v1_app)`): un FastAPI
  por versión. Aislamiento máximo, pero docs fragmentadas y hay que replicar el
  theming de Swagger/ReDoc por sub-app.
- **D — Librería/decoradores** (`fastapi-versioning`): descartada por meter magia
  y una dependencia externa contra el estilo explícito del repo.

## Matriz de decisión (0–10; 10 = mejor)

En *Complejidad* se puntúa la **simplicidad** (10 = menos complejo). Contexto:
se planea **añadir más países** a futuro.

| Criterio | A · Router posee versión | B · Carpeta por versión | C · Sub-apps montadas |
|---|:---:|:---:|:---:|
| Eficiencia (runtime/overhead) | 9 | 8 | 6 |
| Efectividad (versión × país) | 9 | 8 | 8 |
| Escalabilidad (versiones + países) | 9 | 6 | 6 |
| Mantenibilidad (DRY, drift) | 9 | 5 | 5 |
| Complejidad (simplicidad) | 8 | 6 | 4 |
| Adaptación al negocio (multi-país) | 9 | 6 | 6 |
| **Total /60** | **53** | **39** | **35** |
| **Promedio** | **8.8** | **6.5** | **5.8** |

## Decisión: **Opción A**

Motivos frente al futuro multi-país:

- **Escalabilidad ortogonal**: país = incluir un controller en el router de la
  versión; versión = nuevo módulo router que reusa los controllers válidos (bump
  parcial). B y C **duplican** la capa de contrato y multiplican el
  mantenimiento en la matriz versión × país.
- **Mantenibilidad**: `services/` y `models/` compartidos, sin drift; en un v2
  solo cambian las rutas que realmente rompen.
- **Complejidad/eficiencia**: una sola app FastAPI (docs/theming Swagger–ReDoc
  intactos, sin replicar middleware por versión).

## Estructura resultante

```
api/controller/venezuela_controller.py   # controller de país, neutro a la versión
api/controller/argentina_controller.py   # (futuro) otro país
api/router/v1.py                          # arma el APIRouter de v1 incluyendo los controllers
# api/router/v2.py                        # (futuro) reusa lo válido; solo cambia lo que rompe
# main.py monta v1 con API_V1_STR (y v2 con API_V2_STR cuando exista)
```

- El prefijo de versión sigue **centralizado** en `Constants.API_V1_STR` (y
  `Constants.API_V2_STR` cuando aplique), nunca hardcodeado en cada controller.
- **Agregar un país**: crear su controller e incluir su router en `api/router/v1.py`.
- **Agregar una versión**: crear `api/router/v2.py` y montarlo en `main.py` con
  `API_V2_STR`, sin tocar el código de v1.
- **Schemas versionados**: mientras el contrato no diverja, `models/schemas.py`
  se comparte. Cuando una versión rompa el contrato, sus schemas vivirán junto a
  su router (p. ej. `api/router/v2_schemas.py` o un paquete `api/router/v2/`),
  dejando los de v1 intactos.
- La documentación (OpenAPI/Swagger/ReDoc) sigue funcionando con el theming
  actual, al ser una única app.
