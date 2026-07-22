import os


class Config:

    DATABASE_URL = os.getenv("DATABASE_URL")

    OFFICIAL_URL = os.getenv("OFFICIAL_MARKET_DATA_PROVIDER_URL")

    PARALLEL_MARKET_A_URL = os.getenv("MARKET_DATA_PROVIDER_A_URL")

    PARALLEL_MARKET_B_URL = os.getenv("MARKET_DATA_PROVIDER_B_URL")

    PARALLEL_MARKET_C_URL = os.getenv("MARKET_DATA_PROVIDER_C_URL")

    # D queda asignado a Airtm (rates.airtm.io); Exchange Monitor usa F.
    PARALLEL_MARKET_D_URL = os.getenv("MARKET_DATA_PROVIDER_D_URL")

    PARALLEL_MARKET_E_URL = os.getenv("MARKET_DATA_PROVIDER_E_URL")

    PARALLEL_MARKET_F_URL = os.getenv("MARKET_DATA_PROVIDER_F_URL")

    # Variables de entorno requeridas para arrancar la app.
    # (nombre_de_variable, requiere_esquema_http)
    _REQUIRED_ENV = (
        ("DATABASE_URL", False),
        ("OFFICIAL_MARKET_DATA_PROVIDER_URL", True),
        ("MARKET_DATA_PROVIDER_A_URL", True),
        ("MARKET_DATA_PROVIDER_B_URL", True),
        ("MARKET_DATA_PROVIDER_C_URL", True),
        ("MARKET_DATA_PROVIDER_D_URL", True),
        ("MARKET_DATA_PROVIDER_E_URL", True),
        ("MARKET_DATA_PROVIDER_F_URL", True),
    )

    @classmethod
    def validate(cls):
        """Valida (fail-fast) que las variables de entorno requeridas existan.

        Se ejecuta al arrancar la app. Lanza ``EnvironmentError`` con un mensaje
        que **nombra** la variable faltante o mal formada, en lugar del error
        críptico de httpx ("Request URL is missing an 'http://' ... protocol.")
        que aparecería tarde, en cada request, al construirse URLs como
        ``"None/..."``.

        No expone el valor de las variables (solo el nombre) para no filtrar
        secretos.
        """
        missing = []
        invalid_scheme = []
        for name, needs_http in cls._REQUIRED_ENV:
            value = os.getenv(name)
            if not value or not value.strip():
                missing.append(name)
            elif needs_http and not value.strip().lower().startswith(("http://", "https://")):
                invalid_scheme.append(name)

        errors = []
        if missing:
            errors.append(
                "Faltan variables de entorno requeridas (defínelas en .env): "
                + ", ".join(missing)
            )
        if invalid_scheme:
            errors.append(
                "Estas variables de entorno deben incluir el esquema http:// o https://: "
                + ", ".join(invalid_scheme)
            )
        if errors:
            raise EnvironmentError(" | ".join(errors))
