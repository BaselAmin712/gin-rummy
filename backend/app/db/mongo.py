import logging
import app.utils.globals as globals
from pymongo import MongoClient

logger = logging.getLogger(__name__)

def init_db(db_name="ginrummy_db", collection_name="games", host="192.168.68.194", port=27017):
    logger.info("Initializing MongoDB connection...")
    try:
        uri = f"mongodb://{host}:{port}"
        globals.client = MongoClient(uri)
        db = globals.client[db_name]
        globals.games_collection = db[collection_name]
        logger.info("MongoDB connected to %s.%s", db_name, collection_name)
    except Exception as e:
        logger.exception("Failed to connect to MongoDB.")
        raise e

def close_db():
    if globals.client:
        logger.info("Closing MongoDB client...")
        globals.client.close()
    globals.client = None
    globals.games_collection = None
