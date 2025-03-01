import pytest
from fastapi.testclient import TestClient
from pymongo import MongoClient
from app import app, startup_db_client, shutdown_db_client

# Use a test database instead of the main one
TEST_DB_NAME = "test_ginrummy_db"
TEST_COLLECTION_NAME = "test_games"

# Override the MongoDB client to use a test database
@pytest.fixture(scope="module")
def test_db():
    """
    Setup a test MongoDB database before running tests.
    Cleanup after tests are completed.
    """
    client = MongoClient("mongodb://192.168.68.194:27017")  # Use the correct IP of your MongoDB server
    test_db = client[TEST_DB_NAME]
    test_collection = test_db[TEST_COLLECTION_NAME]

    # Ensure the collection is empty before running tests
    test_collection.delete_many({})

    yield test_collection  # Provide the collection to the tests

    # Cleanup after tests
    test_collection.delete_many({})
    client.drop_database(TEST_DB_NAME)  # Remove test DB after tests


@pytest.fixture(scope="module")
def test_client():
    """
    Setup FastAPI test client.
    """
    startup_db_client(TEST_DB_NAME, TEST_COLLECTION_NAME)  # Initialize MongoDB connection
    client = TestClient(app)
    yield client
    shutdown_db_client()  # Close MongoDB connection


# --------------------------------------------------------
# ✅ TEST CASES
# --------------------------------------------------------

def test_root_endpoint(test_client):
    """ Test the root `/` endpoint """
    response = test_client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Gin Rummy Backend"}


def test_create_game(test_client, test_db):
    """ Test creating a new game """
    response = test_client.post("/game", json={"player_name": "Basel"})
    assert response.status_code == 200  # Success
    json_data = response.json()

    # Check if game was created
    assert "game_id" in json_data
    assert json_data["players"] == ["Basel"]
    assert json_data["scores"] == {"Basel": 0}

    # Verify in MongoDB
    stored_game = test_db.find_one({"game_id": json_data["game_id"]})
    assert stored_game is not None
    assert stored_game["players"] == ["Basel"]


def test_join_game(test_client, test_db):
    """ Test joining an existing game """
    # First, create a game
    game_data = {"player_name": "Alice"}
    response = test_client.post("/game", json=game_data)
    assert response.status_code == 200
    game_id = response.json()["game_id"]

    # Now, try to join the game with another player
    response = test_client.post("/game", json={"player_name": "Bob", "game_id": game_id})
    assert response.status_code == 200
    json_data = response.json()

    assert "game_id" in json_data
    assert set(json_data["players"]) == {"Alice", "Bob"}
    assert "Bob" in json_data["scores"] and json_data["scores"]["Bob"] == 0

    # Verify update in MongoDB
    stored_game = test_db.find_one({"game_id": game_id})
    assert set(stored_game["players"]) == {"Alice", "Bob"}


def test_game_full(test_client, test_db):
    """ Test that a third player cannot join a full game """
    game_data = {"player_name": "Charlie"}
    response = test_client.post("/game", json=game_data)
    assert response.status_code == 200
    game_id = response.json()["game_id"]

    # Join the game with 2 players
    test_client.post("/game", json={"player_name": "Dave", "game_id": game_id})

    # Attempt a third player join (should fail)
    response = test_client.post("/game", json={"player_name": "Eve", "game_id": game_id})
    assert response.status_code == 400
    assert response.json()["detail"] == "Game is full. Cannot join a 2-player Gin Rummy game."


def test_invalid_action(test_client, test_db):
    """ Test that an invalid action is rejected """
    game_data = {"player_name": "Frank"}
    response = test_client.post("/game", json=game_data)
    assert response.status_code == 200
    game_id = response.json()["game_id"]

    # Attempt an invalid action
    action_data = {"player_name": "Frank", "action": "invalid_action"}
    response = test_client.post(f"/game/{game_id}/action", json=action_data)
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid action."


def test_get_game_state(test_client, test_db):
    """ Test retrieving the game state """
    game_data = {"player_name": "Grace"}
    response = test_client.post("/game", json=game_data)
    assert response.status_code == 200
    game_id = response.json()["game_id"]

    # Fetch the game state
    response = test_client.get(f"/game/{game_id}")
    assert response.status_code == 200
    json_data = response.json()

    assert json_data["game_id"] == game_id
    assert json_data["players"] == ["Grace"]


def test_get_non_existent_game(test_client):
    """ Test retrieving a non-existent game """
    response = test_client.get("/game/nonexistentgame123")
    assert response.status_code == 404
    assert response.json()["detail"] == "Game not found."
