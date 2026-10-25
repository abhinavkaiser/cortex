"""Prerequisite metadata is independent of teaching/assessment versions."""
from sqlalchemy import Boolean,CheckConstraint,ForeignKey,JSON,String,Text
from sqlalchemy.orm import Mapped,mapped_column
from app.core.db import Base


class PreparationProfile(Base):
    __tablename__='preparation_profiles'
    __table_args__=(CheckConstraint('(course_id IS NOT NULL AND lesson_id IS NULL) OR (course_id IS NULL AND lesson_id IS NOT NULL)',name='one_preparation_owner'),)
    id:Mapped[int]=mapped_column(primary_key=True)
    course_id:Mapped[int|None]=mapped_column(ForeignKey('courses.id'),unique=True,nullable=True)
    lesson_id:Mapped[int|None]=mapped_column(ForeignKey('lessons.id'),unique=True,nullable=True)
    statement:Mapped[str]=mapped_column(Text,default='')
    beginner:Mapped[bool]=mapped_column(Boolean,default=False)
    course_slugs:Mapped[list]=mapped_column(JSON,default=list)
    lesson_slugs:Mapped[list]=mapped_column(JSON,default=list)
    managed_version:Mapped[str|None]=mapped_column(String(64),nullable=True)
