from pydantic import BaseModel


class LoginResponseDTO(BaseModel):
    access_token: str
    token_type: str
    vstitch_user_id: int
    vstitch_user_name: str
