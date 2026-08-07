from pydantic import BaseModel


class PasswordResetResponseDTO(BaseModel):
    status: str
