from pydantic import BaseModel, Field

class TapoDeviceCreateDto(BaseModel):
    ip: str = Field(..., example="192.168.31.110")
    email: str = Field(..., example="user@example.com")
    password: str = Field(..., example="secret123")
    power_watt: int = Field(0, example=2000, description="Estimated power consumption of the device in watts")
    priority: int = Field(0, example=1, description="Priority level of the device (lower means higher priority)")