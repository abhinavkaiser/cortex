from typing import Literal
from pydantic import BaseModel,ConfigDict,Field


class PreparationItem(BaseModel):
    kind:Literal['course','lesson']
    slug:str
    id:int
    title:str
    url:str


class PreparationOut(BaseModel):
    statement:str
    beginner:bool
    items:list[PreparationItem]
    verified:bool


class PreparationWrite(BaseModel):
    model_config=ConfigDict(extra='forbid')
    statement:str=Field(min_length=15,max_length=4000)
    beginner:bool=False
    course_slugs:list[str]=Field(default_factory=list,max_length=30)
    lesson_slugs:list[str]=Field(default_factory=list,max_length=50)
