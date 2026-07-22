---
description: Al agregar, renombrar o eliminar una variable de entorno leída por Config, obliga a sincronizar .env.example, _REQUIRED_ENV y el README en el MISMO cambio. Aplica cada vez que un feature/fix toque la configuración por entorno (nuevas fuentes, credenciales, flags, URLs de proveedores).
---
# Variables de Entorno

Las variables de entorno son la configuración del proyecto fuera del código. La app las lee en `api/core/config/config.py` (`Config`) y **valida al arrancar** (`Config.validate()`, fail-fast) que las requeridas existan, nombrando la faltante. La plantilla pública `/.env.example` es la **única fuente de onboarding**: un dev nuevo debe poder levantar el proyecto copiándola.

Por eso, agregar o quitar una variable no es un cambio de una sola línea: si `.env.example` queda desincronizado, el onboarding se rompe silenciosamente y los despliegues fallan al arrancar.

## Cuándo aplica

Cada vez que un cambio **agregue, renombre o elimine** una variable de entorno leída por `Config` (nuevas fuentes de datos, credenciales, flags, URLs de proveedores, etc.).

## Checklist obligatorio (en el MISMO PR)

Al tocar una variable de entorno, **todos** estos artefactos deben quedar consistentes:

1. **`Config`** (`api/core/config/config.py`): declara el atributo con `os.getenv("NOMBRE")`. Si es obligatoria para arrancar, agrégala a `_REQUIRED_ENV` con el flag de esquema http (`True` si debe ser una URL `http(s)://`).
2. **`.env.example`**: agrega/renombra/elimina la clave. Sus claves deben **coincidir exactamente** con las variables requeridas de `_REQUIRED_ENV` (ni de más ni de menos). **Nunca subas URLs reales de proveedores ni secretos**: usa siempre un placeholder genérico (ej. `https://provider-a.example.com`, `postgresql://usuario:password@localhost:5432/nombre_db`). Los valores reales viven solo en `.env` (gitignored) y en el entorno de despliegue (Vercel).
3. **README** (sección "Configurar variables de entorno"): documenta la variable (qué es), **sin** exponer la URL real ni el nombre del proveedor; usa el mismo placeholder que en `.env.example`.
4. **Entornos de despliegue**: como la validación es fail-fast, una variable **requerida** debe existir en **todos** los entornos (Vercel Preview y Production) antes de desplegar, o la app no arranca. Menciónalo en la descripción del PR.

> Nomenclatura de proveedores del proyecto: `*_MARKET_DATA_PROVIDER_*_URL` (deben incluir el esquema `https://`). Los valores de tipo "constante de código" (no secretos ni por-entorno) van en `Constants`, no en env vars — ver `constants-centralization.md`.

## Verificación rápida

`.env.example` no debe quedar ignorado por `.gitignore` (existe la excepción `!.env.example` frente a `.env*`). Comprueba que sea rastreable y que sus claves cuadren con `_REQUIRED_ENV`:

```bash
git add .env.example && git status --short .env.example   # debe aparecer como rastreado
```

## Excepción

Variables puramente locales/opcionales de desarrollo que no lee `Config` ni afectan el arranque (p. ej. flags de un script suelto) no requieren entrar en `_REQUIRED_ENV`, pero **sí** conviene documentarlas en `.env.example` si un dev nuevo las necesitaría.
