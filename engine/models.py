import json
from typing import List, Optional
from pydantic import BaseModel, field_serializer


class CustomBaseModel(BaseModel):
    pass


class InitialExtractedObject(CustomBaseModel):
    url: str
    title: str  # Job Title
    company: str
    content: str  # Page Content


class LLMExtractedObject(CustomBaseModel):
    url: str
    title: str
    company: str
    salary: Optional[str] = None
    location: Optional[str] = None
    responsibilities: Optional[List[str]] = None
    requirements: List[str]
    extras: Optional[List[str]] = None

    @field_serializer("responsibilities", "requirements", "extras")
    def serialize_list(self, value: Optional[List[str]]) -> str:
        return json.dumps(value) if value is not None else None