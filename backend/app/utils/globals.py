from pymongo import MongoClient
client: MongoClient = None
games_collection = None
PROD_MODE = True