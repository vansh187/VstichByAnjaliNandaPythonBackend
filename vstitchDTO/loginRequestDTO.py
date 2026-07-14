from pydantic import BaseModel, Field


class LoginRequestDTO(BaseModel):
    vstitch_user_name: str = Field(..., min_length=3, max_length=250)
    password: str = Field(..., min_length=1, max_length=250)
