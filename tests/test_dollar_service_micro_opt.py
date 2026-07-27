"""Issue #49: micro-optimizaciones en DollarService.

- ``createCurrency`` usaba ``Helper().getZoneTime()`` dos veces por moneda
  (dos instancias nuevas). Ahora reutiliza ``self.helper`` con una única fuente
  de tiempo para ambas fechas.
- ``serialize_with_image`` reconstruía el dict ``platform_images`` en cada
  llamada. Ahora es una constante de clase (``PLATFORM_IMAGES``), definida una
  sola vez.

Estos tests fijan esas garantías sin cambiar el contrato de respuesta.
"""
from api.services.dollar_services import DollarService
from api.utils.constants.constants import Constants as c


service = DollarService()


def test_create_currency_uses_single_time_source():
    """createDate y updateDate provienen de una única lectura de tiempo."""
    cur = service.createCurrency("USD", "Dolar", 1.0, c.BCV_NAME)
    assert cur.createDate == cur.updateDate


def test_platform_images_is_shared_class_constant():
    """El mapa de logos es una constante de clase, no se reconstruye por llamada."""
    assert "PLATFORM_IMAGES" in vars(DollarService)
    # La misma referencia se comparte entre instancias (no se recrea).
    assert DollarService().PLATFORM_IMAGES is DollarService().PLATFORM_IMAGES


def test_serialize_with_image_resolves_logo_and_contract():
    """serialize_with_image mantiene el contrato: añade platform_img correcto."""
    cur = service.createCurrency("USD", "Dolar", 1.0, c.BINANCE_NAME)
    data = service.serialize_with_image(cur)
    assert data["platform_img"] == c.BINANCE_LOGO_URL
    # Plataforma desconocida degrada a cadena vacía (contrato previo).
    unknown = service.createCurrency("USD", "Dolar", 1.0, "Desconocida")
    assert service.serialize_with_image(unknown)["platform_img"] == ""
