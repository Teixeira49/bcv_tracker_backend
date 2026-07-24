<div align="center"> <img alt="image" src="https://github.com/user-attachments/assets/4654c3d3-ec12-444f-a793-928a57611417" /> </div>

# BCV Tracker Backend (DolarTracker) 🚀

Este proyecto es el motor (Backend) de la aplicación **BCV Tracker**, diseñado para centralizar y monitorear las tasas de cambio de divisas en Venezuela. El sistema obtiene información en tiempo real de fuentes oficiales y alternativas para ofrecer datos precisos sobre el mercado cambiario.

## 📝 De que va el proyecto

El **BCV Tracker Backend** es una API RESTful desarrollada con **FastAPI** que automatiza la recolección de datos de diversas plataformas financieras. Su objetivo principal es proveer una fuente confiable de información sobre el valor del dólar y otras monedas (Euro, Bitcoin, Tether) frente al Bolívar (VES), permitiendo tanto consultas en vivo como el almacenamiento de históricos en una base de datos.

## ✨ Features del Proyecto

- **Monitoreo Multi-fuente**: Obtiene tasas de:
  - **BCV (Banco Central de Venezuela)**: Raspado (scraping) directo del sitio oficial.
  - **Binance P2P**: Tasas promedio de compra y venta para USDT y USDC.
  - **Bybit P2P**: Tasas de compra y venta para USDT y USDC (con degradación elegante por par).
  - **Yadio.io**: Tasas de mercado paralelo y criptomonedas.
  - **Exchange Monitor**: Agregador de mercados. Como el sitio renderiza las tasas por JavaScript, se resuelve con un scraping híbrido (token CSRF del HTML + endpoint de datos JSON); se expone su valor propio, el promedio estimado y los mercados que reporta.
- **Procesamiento Concurrente**: Utiliza `asyncio` y `httpx` para realizar múltiples peticiones en paralelo, garantizando tiempos de respuesta ultrarrápidos.
- **Persistencia de Datos**: Integración con PostgreSQL (via SQLAlchemy) para guardar las últimas tasas y calcular variaciones (ROC - Rate of Change).
- **Cálculos Inteligentes**: Generación de promedios para el mercado de Binance P2P.
- **Preparado para Cloud**: Configuración lista para desplegar en **Vercel** y soporte para **Docker**.
- **Manejo de Errores Robusto**: Sistema de recuperación ante fallos en la inicialización y trazabilidad de errores.

## 🏗️ Arquitectura del Proyecto

El proyecto sigue una arquitectura limpia dividida en capas para facilitar su mantenimiento y escalabilidad:

- **Controllers**: Manejan las peticiones HTTP y la definición de rutas.
- **Services**: Contienen la lógica de negocio (scraping, cálculos, integración con APIs externas).
- **Models**: Definen la estructura de los datos (Pydantic para validación y SQLAlchemy para la BD).
- **Core/Utils**: Funcionalidades transversales como clientes HTTP, constantes y helpers.

### Diagrama de Arquitectura

```mermaid
graph TD
    User(["App Mobile / Cliente"]) --> API["FastAPI Entry Point Limpio"]
    
    API --> DollarController["Dollar Controller"]
    API --> DocsController["Docs Controller"]
    API --> HealthController["Health Controller"]
    
    DollarController --> DollarService["Dollar Service"]
    
    subgraph Core_Business ["Lógica de Negocio"]
        DollarService --> Scraper["BCV Scraper"]
        DollarService --> BinanceAPI["Binance API"]
        DollarService --> BybitAPI["Bybit API"]
        DollarService --> YadioAPI["Yadio API"]
        DollarService --> EMScraper["Exchange Monitor (CSRF + JSON)"]
        DollarService --> DB_Service["Database Service"]
        DB_Service --> Postgres[("PostgreSQL DB")]
    end
    
    subgraph UI_Docs ["Interfaces y Documentación"]
        DocsController --> SwaggerUI["Swagger UI - Dark Theme"]
        DocsController --> ReDocUI["ReDoc UI - Custom Theme"]
    end
    
    subgraph Monitoreo ["Estado del Sistema"]
        HealthController --> HealthUI["Health Check HTML"]
        HealthController --> HealthJSON["Health Status JSON"]
    end
```

## 📦 Dependencias Requeridas

Las principales librerías utilizadas en este proyecto son:

- **FastAPI**: Framework web moderno y rápido.
- **Uvicorn**: Servidor ASGI de alto rendimiento.
- **BeautifulSoup4**: Para el raspado de la web del BCV.
- **SQLAlchemy & Alembic**: Para la gestión de la base de datos y migraciones.
- **HTTPX**: Cliente HTTP asíncrono.
- **PostgreSQL**: Motor de base de datos preferido.
- **Python-dotenv**: Gestión de variables de entorno.

## 🚀 Instalación y Despliegue

### Requisitos Previos
- Python 3.9 o superior.
- Una instancia de PostgreSQL.

### Instalación Local
1. **Clonar el repositorio**:
   ```bash
   git clone https://github.com/Teixeira49/bcv_tracker_backend.git
   cd bcv_tracker_backend
   ```

2. **Crear el entorno virtual**:
   ```bash
   python -m venv venv
   ```

3. **Activar el entorno e instalar dependencias**:
   ```bash
   source venv/bin/activate  # En Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

4. **Configurar variables de entorno**:
   Copia la plantilla `.env.example` a `.env` y rellena los valores. La app valida **todas** las variables requeridas al arrancar; si falta alguna, aborta con un mensaje que nombra la variable faltante.
   ```bash
   cp .env.example .env
   ```
   ```env
   # Base de datos (PostgreSQL)
   DATABASE_URL=postgresql://usuario:password@localhost:5432/nombre_db

   # Fuentes de datos externas (deben incluir el esquema http:// o https://)
   OFFICIAL_MARKET_DATA_PROVIDER_URL=https://official-provider.example.com
   MARKET_DATA_PROVIDER_A_URL=https://provider-a.example.com
   MARKET_DATA_PROVIDER_B_URL=https://provider-b.example.com
   MARKET_DATA_PROVIDER_C_URL=https://provider-c.example.com
   MARKET_DATA_PROVIDER_D_URL=https://provider-d.example.com
   MARKET_DATA_PROVIDER_E_URL=https://provider-e.example.com
   MARKET_DATA_PROVIDER_F_URL=https://provider-f.example.com
   MARKET_DATA_PROVIDER_G_URL=https://provider-g.example.com
   MARKET_DATA_PROVIDER_H_URL=https://provider-h.example.com
   ```
   > Las URLs mostradas son **placeholders**. Coloca las URLs reales de los proveedores solo en tu `.env` local y en las variables del entorno de despliegue (Vercel), nunca en archivos versionados. El `.env` está en `.gitignore` y nunca se versiona (sí se versiona `.env.example`).

5. **Inicializar / migrar el esquema**:

   El esquema se gestiona con **Alembic**. La configuración vive en `alembic.ini` y las migraciones en `migrations/` (`migrations/versions/` contiene la línea base `0001_initial_schema`, con las tablas `currencies` y `platform_dates`). Alembic toma la URL de la BD de la variable de entorno `DATABASE_URL` (la misma que usa la app; no se hardcodea en `alembic.ini`).

   Para crear/actualizar el esquema en tu base de datos:
   ```bash
   alembic upgrade head
   ```

   Al modificar los modelos (`api/models/`), genera una nueva migración:
   ```bash
   alembic revision --autogenerate -m "descripción del cambio"
   alembic upgrade head
   ```

   > Además, al **arrancar** la app (`lifespan` de `api/main.py`) se ejecuta `init_db()` una sola vez: un `create_all` idempotente que garantiza que las tablas existan en entornos efímeros (serverless / cold start). No sustituye a las migraciones —Alembic es la fuente de verdad del esquema versionado—, solo evita que un cold start sin `alembic upgrade head` previo deje la app sin tablas.

6. **Iniciar el servidor**:
   ```bash
   uvicorn api.main:app --reload
   ```

### Despliegue en Vercel
Este proyecto está configurado para Vercel. Solo necesitas conectar tu repositorio a Vercel y se detectará automáticamente el archivo `vercel.json` y la aplicación en `api/main.py`.

## 🤖 Tooling Agéntico

Este repositorio incluye convenciones y capacidades versionadas para desarrollo asistido por IA (skills, rules y roles) en `.agents/`, más la config compartida en `.claude/pr-config.json` y el lockfile `skills-lock.json`. Al clonar, todo el equipo dispone de las mismas reglas sin configuración extra. Consulta el detalle en [CONTRIBUTING.md → Tooling Agéntico](CONTRIBUTING.md#-tooling-agéntico-agents-y-claude).

## 📱 Aplicación Front-end (Mobile)

Este backend alimenta la siguiente aplicación móvil:
👉 [BCV Tracker App (Mobile Front)](https://github.com/Teixeira49/bcv_tracker_app.git)
