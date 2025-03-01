import uuid
import logging
from typing import Optional, List, Dict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from pymongo import MongoClient
from bson import ObjectId

# ------------------------------------------------------------
# Logging Setup
# ------------------------------------------------------------
# Configure logging to show DEBUG level and above
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# ------------------------------------------------------------
# Pydantic Models
# ------------------------------------------------------------
class GameState(BaseModel):
    """
    Represents a game's main data.
    
    _id (ObjectId) is the internal MongoDB ID. We'll store it
    as a string in the 'id' field for easier JSON serialization.
    """
    # id: Optional[str] = Field(alias="_id")
    game_id: str
    players: List[str] = []
    scores: Dict[str, int] = Field(default_factory=dict)

    class Config:
        # Allow population by field name so that _id can map to id
        allow_population_by_field_name = True

class CreateJoinGameRequest(BaseModel):
    player_name: str
    game_id: Optional[str] = None

class ActionRequest(BaseModel):
    player_name: str
    action: str
    payload: Optional[dict] = None

# ------------------------------------------------------------
# FastAPI App
# ------------------------------------------------------------
app = FastAPI()

# Global references to MongoDB client and collection
client: MongoClient = None
games_collection = None

# ------------------------------------------------------------
# Startup / Shutdown Events
# ------------------------------------------------------------
@app.on_event("startup")
def startup_db_client(DB_NAME = "ginrummy_db", COLLECTION_NAME = "games"):
    """
    Connect to MongoDB (synchronously) on startup.
    """
    global client, games_collection
    logger.info("Starting up MongoDB client...")
    try:
        client = MongoClient("mongodb://192.168.68.194:27017")
        db = client[DB_NAME]
        games_collection = db[COLLECTION_NAME]
        logger.info("MongoDB client connected successfully.")
    except Exception as e:
        logger.exception("Failed to connect to MongoDB.")
        raise e

@app.on_event("shutdown")
def shutdown_db_client():
    """
    Close the MongoDB connection when the app shuts down.
    """
    global client
    if client:
        logger.info("Closing MongoDB client...")
        client.close()
        logger.info("MongoDB client closed.")

# ------------------------------------------------------------
# Root Endpoint
# ------------------------------------------------------------
@app.get("/")
def root():
    logger.debug("Handling request at root endpoint.")
    return {"message": "Gin Rummy Backend"}

# ------------------------------------------------------------
# Create or Join Game
# ------------------------------------------------------------
@app.post("/game")
def create_or_join_game(request: CreateJoinGameRequest):
    """
    POST /game
    - If request.game_id is not provided, create a new game in MongoDB.
    - If request.game_id is provided, attempt to join that existing game.
    Returns the GameState from MongoDB.

    Now limited to 2 players maximum in a Gin Rummy game.
    """
    logger.debug("Received Create/Join Game request: %s", request)
    
    player_name = request.player_name.strip()
    if not player_name:
        logger.warning("No player_name provided or player_name is empty.")
        raise HTTPException(status_code=400, detail="player_name must not be empty.")

    if request.game_id:
        # Join existing game
        logger.info("Attempting to join game with ID: %s", request.game_id)
        existing_game = games_collection.find_one({"game_id": request.game_id})
        if not existing_game:
            logger.error("Game not found with ID: %s", request.game_id)
            raise HTTPException(status_code=404, detail="Game not found.")

        game_state = GameState(**existing_game)
        # If the game already has 2 players and this player isn't already in it, reject
        if len(game_state.players) >= 2 and player_name not in game_state.players:
            logger.warning("Game %s is already full (2 players).", request.game_id)
            raise HTTPException(
                status_code=400,
                detail="Game is full. Cannot join a 2-player Gin Rummy game."
            )

        # If the player is not in the game yet, add them
        if player_name not in game_state.players:
            game_state.players.append(player_name)
            logger.debug("Adding player '%s' to game '%s'.", player_name, request.game_id)
            if player_name not in game_state.scores:
                game_state.scores[player_name] = 0
            
            games_collection.update_one(
                {"_id": existing_game["_id"]},
                {"$set": {
                    "players": game_state.players,
                    "scores": game_state.scores
                }}
            )
        else:
            logger.debug("Player '%s' is already in game '%s'.", player_name, request.game_id)

        logger.info("Player '%s' joined or is already in game '%s'.", player_name, request.game_id)
        return game_state

    else:
        # Create a new game (always starts with exactly 1 player)
        logger.info("Creating a new game for player '%s'.", player_name)
        new_game_id = str(uuid.uuid4())
        new_game = GameState(game_id=new_game_id, players=[player_name], scores={player_name: 0})
        
        insert_result = games_collection.insert_one(new_game.dict(by_alias=True))
        logger.debug("Inserted new game with _id: %s", insert_result.inserted_id)
        
        created_game_doc = games_collection.find_one({"_id": insert_result.inserted_id})
        logger.info("New game created with game_id: %s", new_game_id)
        return GameState(**created_game_doc)


# ------------------------------------------------------------
# Make a Move
# ------------------------------------------------------------
@app.post("/game/{game_id}/action")
def make_move(game_id: str, request: ActionRequest):
    """
    POST /game/{game_id}/action
    Allows a player to perform an action (draw, discard, knock, etc.)
    """
    logger.debug("Received action request: Game ID: %s, Action: %s, Player: %s",
                 game_id, request.action, request.player_name)
    
    if not request.player_name:
        logger.warning("Missing player name in action request.")
        raise HTTPException(status_code=400, detail="Missing player name.")

    existing_game = games_collection.find_one({"game_id": game_id})
    if not existing_game:
        logger.error("Game not found for action request, game_id: %s", game_id)
        raise HTTPException(status_code=404, detail="Game not found.")

    game_state = GameState(**existing_game)
    if request.player_name not in game_state.players:
        logger.warning("Player '%s' is not in game '%s'.", request.player_name, game_id)
        raise HTTPException(status_code=400, detail="Player not in this game.")

    action = request.action.lower()
    if action not in ["draw", "discard", "knock"]:
        logger.warning("Invalid action: %s", action)
        raise HTTPException(status_code=400, detail="Invalid action.")

    logger.info("Player '%s' is performing '%s' in game '%s'.",
                request.player_name, action, game_id)

    # Placeholder for real game logic
    if action == "draw":
        logger.debug("Processing draw action for player '%s'.", request.player_name)
        # e.g. draw a card from deck
    elif action == "discard":
        logger.debug("Processing discard action for player '%s'.", request.player_name)
        # e.g. discard a card
    elif action == "knock":
        logger.debug("Processing knock action for player '%s'.", request.player_name)
        # e.g. knock to end the round

    # If you modify the game state, do another update_one here:
    # games_collection.update_one({"_id": existing_game["_id"]}, {"$set": {...}})

    logger.debug("Returning updated game state for game '%s'.", game_id)
    return game_state

# ------------------------------------------------------------
# Get Current Game State
# ------------------------------------------------------------
@app.get("/game/{game_id}")
def get_game_state(game_id: str):
    """
    GET /game/{game_id}
    Retrieves the current state of the specified game.
    """
    logger.debug("Retrieving game state for game_id: %s", game_id)
    existing_game = games_collection.find_one({"game_id": game_id})
    if not existing_game:
        logger.error("No game found for ID: %s", game_id)
        raise HTTPException(status_code=404, detail="Game not found.")

    logger.info("Returning game state for game_id: %s", game_id)
    return GameState(**existing_game)
