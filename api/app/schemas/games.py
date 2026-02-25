from pydantic import BaseModel, field_validator


class BatchRequest(BaseModel):
    appids: list[str]
    recap: bool = False

    @field_validator("appids")
    def validate_appids(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("appids must not be empty")
        if len(v) > 10:
            raise ValueError("Maximum 10 appids per batch")
        return v
