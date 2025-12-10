from pydantic import BaseModel


class UserMeResponse(BaseModel):
    id: int
    username: str
    email: str
