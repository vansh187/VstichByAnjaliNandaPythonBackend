from pydantic import BaseModel


class AdminImageUploadResponseDTO(BaseModel):
    image_url: str
