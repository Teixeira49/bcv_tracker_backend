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

## 🚀 Nuevas Fuentes de Datos

Si deseas agregar un nuevo monitor de divisas:
1. Añade los endpoints necesarios en `DollarEndpoints`.
2. Implementa el método de extracción en `DollarService`.
3. Si requiere persistencia, verifica que el modelo `Currency` sea compatible o actualízalo.
4. Registra el nuevo endpoint en `DollarController`.

---

¡Feliz codificación! Si tienes dudas, abre un **Issue** para discutir tu propuesta antes de empezar.
