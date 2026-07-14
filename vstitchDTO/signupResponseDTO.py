from pydantic import BaseModel


class SignupResponseDTO(BaseModel):
    vstitch_user_id: int
    vstitch_user_name: str
    email: str
    message: str
