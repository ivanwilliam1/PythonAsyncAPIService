# settings.py
from dotenv import load_dotenv
import os

load_dotenv(verbose=True)

MONGODB_HOST = os.getenv("MONGODB_HOST")
MONGODB_PORT = os.getenv("MONGODB_PORT")
MONGODB_PORT = int(MONGODB_PORT) if MONGODB_PORT is not None else MONGODB_PORT
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME")
MONGODB_DB_COLLECTION_NAME = os.getenv("MONGODB_DB_COLLECTION_NAME")
API_PORT = os.getenv("API_PORT")
API_HOST = os.getenv("API_HOST")
DEBUG = True if os.getenv("DEBUG").lower() in ['true', 'yes'] else False
AUTO_RELOAD =True if os.getenv("AUTO_RELOAD").lower() in ['true', 'yes'] else False