"""
Pydantic models for Question and Exam data structures.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class Question(BaseModel):
    """Model for a single exam question."""
    question_number: str
    section: str
    marks: int
    text: str
    content_description: Optional[str] = None
    source_ids: Optional[List[str]] = None
    images: Optional[List[Dict[str, Any]]] = None
    equations: Optional[List[Dict[str, Any]]] = None
    answer_choices: Optional[List[str]] = None


class ExamMetadata(BaseModel):
    """Model for exam metadata."""
    university: str
    faculty: str
    course: str
    date: str
    time: Optional[str] = None
    duration: Optional[str] = None
    source_ids: Optional[List[str]] = None


class Exam(BaseModel):
    """Model for a complete exam."""
    exam_metadata: ExamMetadata
    questions: List[Question]
    
    def get_total_marks(self) -> int:
        """Calculate total marks for the exam."""
        return sum(q.marks for q in self.questions)
    
    def get_difficulty_score(self) -> float:
        """Calculate difficulty score based on marks distribution."""
        total_marks = self.get_total_marks()
        if total_marks == 0:
            return 0.0
        # Higher marks = harder questions typically
        avg_marks_per_question = total_marks / len(self.questions) if self.questions else 0
        # Normalize to 0-1 scale (assuming max 25 marks per question)
        return min(avg_marks_per_question / 25.0, 1.0)


class GeneratedQuestion(BaseModel):
    """Model for a generated question (before validation)."""
    question_number: str
    section: str
    marks: int = 0
    text: str
    answer_choices: Optional[List[str]] = None
    explanation: Optional[str] = None


class GeneratedExam(BaseModel):
    """Model for a generated exam."""
    exam_metadata: ExamMetadata
    questions: List[GeneratedQuestion]
    
    def to_exam(self) -> Exam:
        """Convert GeneratedExam to Exam format."""
        return Exam(
            exam_metadata=self.exam_metadata,
            questions=[
                Question(
                    question_number=q.question_number,
                    section=q.section,
                    marks=q.marks,
                    text=q.text,
                    answer_choices=q.answer_choices
                )
                for q in self.questions
            ]
        )


class ExamGenerationRequest(BaseModel):
    """Model for exam generation request parameters."""
    course: str = "APSC 142 - Introduction to Computer Programming for Engineers"
    target_marks: int = 100
    difficulty: Optional[str] = "medium"  # easy, medium, hard
    sections: Optional[List[str]] = 6
    num_questions: Optional[int] = None
    style_examples_count: int = 5

