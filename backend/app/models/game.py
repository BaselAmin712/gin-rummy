from pydantic import BaseModel, Field
from typing import Optional, List, Dict

class GameState(BaseModel):
    # id: Optional[str] = Field(alias="_id")
    game_id: str
    players: List[str] = []
    scores: Dict[str, int] = Field(default_factory=dict)

    class Config:
        allow_population_by_field_name = True


class CreateJoinGameRequest(BaseModel):
    player_name: str
    game_id: Optional[str] = None


class ActionRequest(BaseModel):
    player_name: str
    action: str
    payload: Optional[dict] = None