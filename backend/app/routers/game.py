import uuid
import logging
import app.utils.globals as globals
from fastapi import APIRouter, HTTPException
from bson.objectid import ObjectId

from app.models.game import (
    GameState,
    CreateJoinGameRequest,
    ActionRequest,
)

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/")
def create_or_join_game(request: CreateJoinGameRequest):
    logger.debug("Received Create/Join Game request: %s", request)
    
    player_name = request.player_name.strip()
    if not player_name:
        logger.warning("No player_name provided or player_name is empty.")
        raise HTTPException(status_code=400, detail="player_name must not be empty.")

    if request.game_id:
        # Join existing game
        logger.info("Attempting to join game with ID: %s", request.game_id)
        existing_game = globals.games_collection.find_one({"game_id": request.game_id})
        if not existing_game:
            logger.error("Game not found with ID: %s", request.game_id)
            raise HTTPException(status_code=404, detail="Game not found.")

        game_state = GameState(**existing_game)
        # If the game already has 2 players and this player isn't in it, reject
        if len(game_state.players) >= 2 and player_name not in game_state.players:
            logger.warning("Game %s is already full (2 players).", request.game_id)
            raise HTTPException(
                status_code=400,
                detail="Game is full. Cannot join a 2-player Gin Rummy game."
            )

        # Add the player if they're not already present
        if player_name not in game_state.players:
            game_state.players.append(player_name)
            if player_name not in game_state.scores:
                game_state.scores[player_name] = 0
            
            globals.games_collection.update_one(
                {"_id": existing_game["_id"]},
                {"$set": {
                    "players": game_state.players,
                    "scores": game_state.scores
                }}
            )
        return game_state

    else:
        # Create a new game (1 player to start)
        logger.info("Creating a new game for player '%s'.", player_name)
        new_game_id = str(uuid.uuid4())
        new_game = GameState(
            game_id=new_game_id,
            players=[player_name],
            scores={player_name: 0}
        )
        
        insert_result = globals.games_collection.insert_one(new_game.dict(by_alias=True))
        created_game_doc = globals.games_collection.find_one({"_id": insert_result.inserted_id})
        logger.info("New game created with game_id: %s", new_game_id)
        return GameState(**created_game_doc)


@router.post("/{game_id}/action")
def make_move(game_id: str, request: ActionRequest):
    logger.debug(
        "Received action request: Game ID: %s, Action: %s, Player: %s",
        game_id,
        request.action,
        request.player_name
    )

    if not request.player_name:
        logger.warning("Missing player name in action request.")
        raise HTTPException(status_code=400, detail="Missing player name.")

    existing_game = globals.games_collection.find_one({"game_id": game_id})
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
    # If you change the game state (e.g., update scores), call games_collection.update_one

    return game_state


@router.get("/{game_id}")
def get_game_state(game_id: str):
    logger.debug("Retrieving game state for game_id: %s", game_id)
    existing_game = globals.games_collection.find_one({"game_id": game_id})
    if not existing_game:
        logger.error("No game found for ID: %s", game_id)
        raise HTTPException(status_code=404, detail="Game not found.")

    logger.info("Returning game state for game_id: %s", game_id)
    return GameState(**existing_game)