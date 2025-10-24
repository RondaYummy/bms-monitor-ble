from typing import Optional

from pydantic import BaseModel, Field


class TapoDeviceCreateDto(BaseModel):
    ip: str = Field(..., example="192.168.31.110")
    email: str = Field(..., example="user@example.com")
    password: str = Field(..., example="secret123")
    power_watt: int = Field(0, example=2000, description="Estimated power consumption of the device in watts")
    priority: int = Field(0, example=1, description="Priority level of the device (lower means higher priority)")

class TapoDeviceUpdateDto(BaseModel):
    email: Optional[str] = Field(None, description="New email for device")
    password: Optional[str] = Field(None, description="New password for device")
    power_watt: Optional[int] = Field(None, description="Manual power_watt override")
    priority: Optional[int] = Field(None, description="Priority level")
    
class TimerRequestDto(BaseModel):
    timer: int = Field(..., gt=0, description="Timer in minutes (integer > 0)")