from typing import Optional

from pydantic import BaseModel


class EchoRequest(BaseModel):
    name: str
    age: int
    sex: str


class EchoParamsResponse(BaseModel):
    age: int
    sex: Optional[str]


class EchoResponse(BaseModel):
    name: str
    params: EchoParamsResponse
