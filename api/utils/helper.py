from datetime import datetime
from zoneinfo import ZoneInfo

class Helper:
    def __init__(self):
        pass

    CARACAS_TZ = ZoneInfo('America/Caracas')
    
    def getZoneTime(self):
        return datetime.now(self.CARACAS_TZ)