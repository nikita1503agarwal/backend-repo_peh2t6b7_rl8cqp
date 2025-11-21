"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class Lkpd(BaseModel):
    user_id: str = Field(..., description="Client-generated user identifier")
    responses: Dict[str, Any] = Field(default_factory=dict, description="LKPD answers or data payload")

class Reflection(BaseModel):
    user_id: str = Field(..., description="Client-generated user identifier")
    reflection_text: str = Field(..., min_length=10, description="Reflection content")

class QuizAttempt(BaseModel):
    user_id: str = Field(..., description="Client-generated user identifier")
    answers: Dict[str, Any] = Field(default_factory=dict, description="Submitted answers")
    score: Optional[int] = Field(None, description="Calculated score")

# Optional helper response schemas
class StatusResponse(BaseModel):
    user_id: str
    has_lkpd: bool
    has_reflection: bool
    last_score: Optional[int] = None
