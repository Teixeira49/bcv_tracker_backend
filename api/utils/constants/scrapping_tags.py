
class ScrappingTags:

    ID_DOLAR = "dolar"

    KEY_DATE = "content"

    KEY_NAME = "id"

    CLASS_DATE = "date-display-single"

    CLASS_CURRENCY = "col-sm-12 col-xs-12"

    CLASS_IMAGE = "icono_bss_blanco1"

    CLASS_CODE = "span"

    CLASS_NAME = "strong"

    # Exchange Monitor — el sitio renderiza las tasas por JavaScript, así que el
    # HTML solo aporta el token CSRF necesario para pedir el JSON de datos. Vive
    # en <meta name="csrf-token" content="...">.
    META_TAG = "meta"

    KEY_META_NAME = "name"

    CSRF_META_NAME = "csrf-token"

    KEY_CONTENT = "content"