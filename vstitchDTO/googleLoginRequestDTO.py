from pydantic import BaseModel, Field


class GoogleLoginRequestDTO(BaseModel):
    id_token: str = Field(..., min_length=1)
