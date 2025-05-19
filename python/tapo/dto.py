from pydantic import BaseModel, Field

class TapoDeviceCreateDto(BaseModel):
    ip: str = Field(..., example="192.168.31.110")
    email: str = Field(..., example="user@example.com")
    password: str = Field(..., example="secret123")