from typing import Any, Iterable
from routes.utils import CustomBase
from pydantic import field_serializer


class Row(CustomBase):
    name: str
    average_salary: float
    median_salary: float

    @field_serializer("average_salary", "median_salary")
    def serialize_floats(self, value: float) -> str:
        reversed_value: list[str] = list(str(round(value))[::-1])

        for i in range(0, len(reversed_value), 3):
            if i:
                reversed_value.insert(i, ",")

        return "".join(reversed_value[::-1])


class PaginatedResponse(CustomBase):
    data: tuple[Any] | list[Any]
    has_next_page: bool
    
class MaxPagesPaginatedResponse(PaginatedResponse):
    max_pages: int