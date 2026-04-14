# BCV Tracker Backend (DolarTracker) 🚀

Este proyecto es el motor (Backend) de la aplicación **BCV Tracker**, diseñado para centralizar y monitorear las tasas de cambio de divisas en Venezuela. El sistema obtiene información en tiempo real de fuentes oficiales y alternativas para ofrecer datos precisos sobre el mercado cambiario.

## 📝 De que va el proyecto

El **BCV Tracker Backend** es una API RESTful desarrollada con **FastAPI** que automatiza la recolección de datos de diversas plataformas financieras. Su objetivo principal es proveer una fuente confiable de información sobre el valor del dólar y otras monedas (Euro, Bitcoin, Tether) frente al Bolívar (VES), permitiendo tanto consultas en vivo como el almacenamiento de históricos en una base de datos.

## ✨ Features del Proyecto

- **Monitoreo Multi-fuente**: Obtiene tasas de:
  - **BCV (Banco Central de Venezuela)**: Raspado (scraping) directo del sitio oficial.
  - **Binance P2P**: Tasas promedio de compra y venta para USDT y USDC.
  - **Yadio.io**: Tasas de mercado paralelo y criptomonedas.
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
    User([App Mobile / Cliente]) --> API[FastAPI Entry Point]
    API --> Controller[Dollar Controller]
    Controller --> Service[Dollar Service]
    
    subgraph Data_Retrieval [Recolección de Datos]
        Service --> Scraper[BCV Scraper - BeautifulSoup]
        Service --> BinanceAPI[Binance P2P API]
        Service --> YadioAPI[Yadio API]
    end
    
    Service --> DB_Service[Database Service]
    DB_Service --> Postgres[(PostgreSQL DB)]
    
    Scraper --> WebBCV[Web Oficial BCV]
    BinanceAPI --> ExtBinance[Binance Servers]
    YadioAPI --> ExtYadio[Yadio Servers]
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
   Crea un archivo `.env` en la raíz con:
   ```env
   DATABASE_URL=postgresql://usuario:password@localhost:5432/nombre_db
   ```

5. **Ejecutar migraciones**:
   ```bash
   alembic upgrade head
   ```

6. **Iniciar el servidor**:
   ```bash
   uvicorn api.main:app --reload
   ```

### Despliegue en Vercel
Este proyecto está configurado para Vercel. Solo necesitas conectar tu repositorio a Vercel y se detectará automáticamente el archivo `vercel.json` y la aplicación en `api/main.py`.

## 📱 Aplicación Front-end (Mobile)

Este backend alimenta la siguiente aplicación móvil:
👉 [BCV Tracker App (Mobile Front)](https://github.com/Teixeira49/bcv_tracker_app.git)