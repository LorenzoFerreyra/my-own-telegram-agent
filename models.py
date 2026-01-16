from pydantic import BaseModel

class TelegramMessage(BaseModel):
    message: dict