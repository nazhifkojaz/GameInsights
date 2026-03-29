from pydantic import BaseModel, ConfigDict


class UserResponse(BaseModel):
    """Response model for user data."""

    model_config = ConfigDict(extra="allow")

    steamid: str
    personaname: str
