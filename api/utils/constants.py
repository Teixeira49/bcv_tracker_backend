import os

class Constants:
    BCV_URL = "https://www.bcv.org.ve/"
    EMPTY_STRING = ""
    EMPTY_SPACE = " "

    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    DB_DIR = os.path.join(BASE_DIR, "data")
    DB_FILE = os.path.join(DB_DIR, "bcv.db")