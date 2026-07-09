# Release Notes - v2.0.0 🚀
**DolarTracker Backend: The Hardening & Versioning Update**
*Fecha de lanzamiento: 8 de Julio de 2026*

---

## 💎 Visión General

La versión **2.0.0** endurece el backend de DolarTracker de cara a producción y
formaliza cómo evoluciona la API. El hito que marca el salto de major es el
**versionado de los endpoints de negocio bajo `/api/v1`** (cambio incompatible),
acompañado de una capa de errores uniforme, validación de configuración al
arranque y correcciones que evitan respuestas silenciosamente incorrectas de las
fuentes de datos. También se profesionaliza el tooling del repositorio (proceso
de CHANGELOG/SemVer, control de despliegues en Vercel y flujo de promoción).

---

## ⚠️ Cambios Incompatibles (Breaking Changes)

- **Endpoints de negocio versionados bajo `/api/v1`** (PR #51, DT-008): las rutas
  de negocio se movieron a un prefijo `/api/v1`. Los consumidores que apuntaban a
  las rutas anteriores **deben actualizar sus URLs** al nuevo prefijo. Este es el
  motivo del incremento a MAJOR.

> Guía de migración: reemplaza las llamadas a las rutas antiguas por su
> equivalente bajo `/api/v1/...`. Los endpoints operativos (p. ej. health)
> permanecen fuera del prefijo de negocio.

---

## 🛠️ Registro de Cambios

### ⚙️ API y Contrato
*   **Versionado `/api/v1`** (DT-008): prefijo de versión para los endpoints de
    negocio, habilitando evolución sin romper a los consumidores en el futuro.
*   **Sobre de error uniforme** (DT-007): todas las respuestas de error de la API
    se renderizan con un envelope consistente y códigos tipados, en vez de
    formatos dispares por endpoint.

### 🐛 Robustez y Correcciones
*   **Validación de entorno al arranque** (DT-004): la app valida las variables de
    entorno requeridas al iniciar y falla temprano con un error claro en vez de
    romperse a mitad de request.
*   **Scraper con errores tipados** (DT-005): ante un fallo de la fuente, el
    scraper lanza un error tipado en lugar de devolver una lista vacía con `200`,
    evitando “éxitos” silenciosos con datos vacíos.
*   **Binance P2P sin `ZeroDivisionError`** (DT-006): se validan las ofertas P2P
    antes de promediar, evitando la división por cero cuando no hay ofertas.

### ♻️ Ingeniería y Estructura
*   **Cliente HTTP asíncrono real** (DT-003): migración de `HttpClient` a `httpx`
    asíncrono real y extracción del timeout HTTP a `Constants`.

### 📝 Proceso, Tooling y Despliegue
*   **CHANGELOG + SemVer formal** (DT-002): proceso documentado de versionado
    semántico y mantenimiento del CHANGELOG.
*   **Tooling agéntico versionado** (DT-001): skills, rules y roles del repo
    quedan versionados.
*   **Control de despliegues en Vercel**: allowlist de ramas que despliegan
    (`preview`, `main`) y flujo de promoción staged a producción.

### ✅ Pruebas
*   Cobertura para el caso de respuesta P2P vacía de Binance (DT-006).
*   Cobertura del sobre de error uniforme y sus códigos (DT-007).

---

## 🚀 Próximos Pasos
*   Implementación de caché avanzada para endpoints de scraping.
*   Integración de autenticación JWT para endpoints administrativos.
*   Dashboard estadístico de variaciones históricas.

---
*DolarTracker - Monitorizando la economía con precisión y elegancia.*
