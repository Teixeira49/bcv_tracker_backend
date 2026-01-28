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
        return datetime.now(self.CARACAS_TZ)