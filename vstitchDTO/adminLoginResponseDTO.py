from pydantic import BaseModel


class AdminLoginResponseDTO(BaseModel):
    access_token: str
    token_type: str
    admin_id: int
    admin_username: str
