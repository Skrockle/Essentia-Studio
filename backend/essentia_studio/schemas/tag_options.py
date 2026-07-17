from pydantic import BaseModel


class TagOptions(BaseModel):
    genres: list[str]
    moods: list[str]
