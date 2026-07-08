# Despliegue y promoción (Vercel · plan Free)

Flujo de promoción controlado: los cambios suben por etapas
`development → preview → main`, se testean en Preview y se promueven
manualmente a Producción. Ninguna rama despliega sola salvo `preview` y `main`.

## Modelo de ramas

```
feature/* ──PR──▶ development        integras cambios · SIN deploy
                     │
                     ▼  merge cuando junta varios cambios
                  preview            ✅ deploy Preview (staging para testear)
                     │
                     ▼  merge / promoción cuando validas
                  main               ✅ deploy Producción
```

| Rama                         | ¿Despliega? | Entorno    |
| ---------------------------- | ----------- | ---------- |
| `main`                       | ✅          | Producción |
| `preview`                    | ✅          | Preview    |
| `development`                | ❌          | —          |
| `feature/*`, `fix/*`, etc.   | ❌          | —          |

El control vive en [`vercel.json`](../vercel.json) → `git.deploymentEnabled`
(patrón `"*": false` + allowlist de `preview` y `main`). Usa minimatch: si una
rama coincide con varias reglas y al menos una es `true`, despliega.

> Para que una rama deje de desplegar, la config de `vercel.json` debe existir
> **en esa rama** (Vercel la lee del commit que dispara el evento). Por eso hay
> que propagarla a `development` y `main` (ver rollout abajo).

## Configuración inicial (una sola vez)

Estos dos pasos requieren tu login de Vercel; no se pueden versionar en el repo.

1. **Apagar el auto-assign de dominios de producción** (habilita el flujo de
   "staged production build" → un merge a `main` queda *Staged*, no sirve
   tráfico hasta que lo promuevas):
   - Dashboard → tu proyecto → **Settings → Environments → Production**
   - Sección **Branch Tracking** → desactiva **Auto-assign Custom Production Domains**

2. **Linkear el CLI** (para promover desde terminal):
   ```bash
   npm i -g vercel@latest
   vercel login
   vercel link          # elige el proyecto bcv_tracker
   ```

Confirma que la **Production Branch** siga siendo `main`
(Settings → Git).

## Rollout inicial de la config

Para que `development` y las feature branches dejen de desplegar, la config de
`vercel.json` tiene que llegar a las ramas base:

```bash
# 1. Landea vercel.json (con git.deploymentEnabled) vía tu flujo normal de PR
#    hasta main.  En cuanto el commit con la config está en una rama, esa rama
#    respeta la regla en el siguiente push.

# 2. Propaga a development
git checkout development && git pull
git merge main            # trae la config
git push

# 3. Crea la rama preview a partir de development
git checkout -b preview
git push -u origin preview   # primer deploy Preview (staging)
```

## Día a día

```bash
# Integrar trabajo (no despliega)
git checkout development
git merge feature/mi-cambio      # vía PR
git push

# Subir a staging para testear (deploy Preview automático)
git checkout preview
git merge development
git push
# → testea en la URL de rama estable:
#   bcv-tracker-git-preview-<scope>.vercel.app
```

## Promover a Producción

Con el auto-assign apagado tienes dos caminos:

### A) Vía Git (merge a main → Staged → promover)

```bash
git checkout main
git merge preview
git push                         # crea un deployment de producción STAGED
```
Luego promuévelo: en Deployments → “…” → **Promote to Production**, o por CLI:
```bash
vercel promote <url-o-id-del-deployment>
```

### B) Vía CLI (build staged directo, sin pasar por main)

```bash
./scripts/promote.sh
```
Equivale a:
```bash
vercel --prod --skip-domain      # build de producción STAGED (no sirve tráfico)
vercel promote <url>             # lo promueve cuando estás listo
```

> ⚠️ Al promover, las variables de entorno cambian de *preview* a las de
> *production*. No puedes usar env vars de preview en un build de producción.

## Rollback

Para volver instantáneamente a un deployment que ya sirvió producción:
```bash
vercel rollback                  # al anterior
vercel rollback <url-o-id>       # a uno específico
```
