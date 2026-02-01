# Modelos de datos

from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime
from enum import Enum

class EnglishLevel(str, Enum):
    BASIC = "basic"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"

class UserProfile(BaseModel):
    chat_id: int
    username: Optional[str]
    first_name: Optional[str]
    level: EnglishLevel = EnglishLevel.BASIC
    registration_date: datetime = Field(default_factory=datetime.now)
    last_activity: datetime = Field(default_factory=datetime.now)
    vocabulary_seen: List[str] = []
    lessons_completed: int = 0
    conversation_context: List[Dict] = []
    
    class Config:
        from_attributes = True

class VocabularyItem(BaseModel):
    id: str
    category: str
    english_word: str
    spanish_translation: str
    example_sentence: str
    complexity: EnglishLevel
    pronunciation: Optional[str]
    
class Lesson(BaseModel):
    id: str
    title: str
    description: str
    content_basic: str
    content_intermediate: str
    content_advanced: str
    exercises: List[Dict]
    duration_minutes: int