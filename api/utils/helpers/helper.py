from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

class Helper:
    def __init__(self):
        pass
    
    try:
        # Intentamos cargar la zona horaria de Caracas
        CARACAS_TZ = ZoneInfo('America/Caracas')
    except ZoneInfoNotFoundError:
        # Si falla (común en Windows sin tzdata), usamos UTC como fallback 
        # para que la app al menos inicie.
        import warnings
        warnings.warn("ZoneInfo 'America/Caracas' no encontrada. Usando UTC como respaldo. Instala 'tzdata'.")
        CARACAS_TZ = timezone.utc
    
    def getZoneTime(self):
        """Devuelve la hora actual en la zona de Caracas (o UTC de respaldo).

        :return: ``datetime`` con tzinfo de ``America/Caracas`` (o UTC si la zona
            no está disponible en el sistema).
        """
        return datetime.now(self.CARACAS_TZ)

    def formatCuValue(self, value: str) -> float:
        """Convierte un valor numérico en formato local (coma decimal) a ``float``.

        :param value: cadena con la tasa (p. ej. ``"782,74"``).
        :return: el valor como ``float`` (p. ej. ``782.74``).
        """
        return float(value.strip().replace(",", "."))

    def rate_of_change(self, previous, current) -> float:
        """Calcula la variación porcentual (ROC) entre dos valores.

        Helper único de ROC del proyecto: lo usan tanto la persistencia
        (``save_currencies_to_db``) como el cálculo en vivo
        (``calculate_live_changes``), para no duplicar la fórmula ni el
        guard de división por cero.

        :param previous: valor previo (base de la comparación).
        :param current: valor actual.
        :return: ``((current - previous) / previous) * 100``; ``0.0`` si
            ``previous`` es ``None``/``0`` (sin base contra la cual comparar).
        """
        if previous and previous != 0:
            return ((current - previous) / previous) * 100
        return 0.0

    def validateDate(self, date_str: str) -> bool:
        """Indica si ``date_str`` (ISO) corresponde a la fecha de hoy en Caracas.

        :param date_str: fecha en formato ISO 8601.
        :return: ``True`` si es la fecha actual; ``False`` si difiere o el
            formato es inválido.
        """
        try:
            date_from_bcv = datetime.fromisoformat(date_str).date()
            return date_from_bcv == Helper().getZoneTime().date()
        except ValueError:
            print("Invalid date format")
            return False