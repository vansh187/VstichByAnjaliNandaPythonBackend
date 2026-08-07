from pydantic import BaseModel


class UpdateLocationResponseDTO(BaseModel):
    status: str
