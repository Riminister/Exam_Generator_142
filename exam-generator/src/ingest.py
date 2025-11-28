"""
Script to load JSON question bank and create vector embeddings.
Includes relevance scoring for difficulty (marks) and date.
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
import chromadb
from chromadb.config import Settings
from dotenv import load_dotenv
from openai import OpenAI

# Handle both relative and absolute imports
try:
    from .models import Exam, Question
except ImportError:
    # When running as script directly
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    from models import Exam, Question

# Load environment variables
load_dotenv(encoding='utf-8')
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY").strip() if os.getenv("OPENAI_API_KEY") else None)


def parse_date(date_str: str) -> datetime:
    """Parse date string to datetime object."""
    try:
        # Try common date formats
        formats = [
            "%B %d, %Y",  # "April 20, 2013"
            "%b %d, %Y",  # "Apr 20, 2013"
            "%Y-%m-%d",   # "2013-04-20"
            "%m/%d/%Y",   # "04/20/2013"
        ]
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        # If all fail, return a default old date
        return datetime(2000, 1, 1)
    except Exception:
        return datetime(2000, 1, 1)


def calculate_relevance_score(exam: Exam, question: Question, current_date: datetime = None) -> float:
    """
    Calculate relevance score for a question based on:
    - Difficulty (marks relative to exam total)
    - Date relevance (newer exams are more relevant)
    """
    if current_date is None:
        current_date = datetime.now()
    
    # Difficulty score: marks / exam_total_marks (normalized)
    exam_total = exam.get_total_marks()
    if exam_total == 0:
        difficulty_score = 0.0
    else:
        # Normalize marks to 0-1 scale
        difficulty_score = min(question.marks / exam_total, 1.0)
    
    # Date relevance: newer exams are more relevant
    try:
        exam_date = parse_date(exam.exam_metadata.date)
        days_old = (current_date - exam_date).days
        # Exponential decay: more recent = higher score
        # Exams older than 10 years get very low score
        date_score = max(0.0, 1.0 - (days_old / 3650.0))  # 10 years = 0 score
    except Exception:
        date_score = 0.5  # Default if date parsing fails
    
    # Combined relevance (weighted)
    # 60% difficulty, 40% date relevance
    relevance = (0.6 * difficulty_score) + (0.4 * date_score)
    
    return relevance


def create_embedding(text: str) -> List[float]:
    """Create embedding for text using OpenAI."""
    try:
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"Error creating embedding: {e}")
        return []


def load_question_bank(json_path: str) -> List[Exam]:
    """Load exams from JSON file."""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    exams = []
    for exam_data in data:
        try:
            exam = Exam(**exam_data)
            exams.append(exam)
        except Exception as e:
            print(f"Error parsing exam: {e}")
            continue
    
    return exams


def ingest_to_vector_db(json_path: str, collection_name: str = "exam_questions"):
    """
    Load question bank and create vector embeddings in ChromaDB.
    Each question is embedded with its text and metadata.
    """
    # Load exams
    print("Loading question bank...")
    exams = load_question_bank(json_path)
    print(f"Loaded {len(exams)} exams")
    
    # Initialize ChromaDB (in exam-generator directory)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    db_path = project_root / "chroma_db"
    
    chroma_client = chromadb.PersistentClient(
        path=str(db_path),
        settings=Settings(anonymized_telemetry=False)
    )
    
    # Get or create collection
    try:
        collection = chroma_client.get_collection(name=collection_name)
        print(f"Found existing collection: {collection_name}")
        # Clear existing data
        collection.delete()
        print("Cleared existing collection")
    except Exception:
        pass
    
    collection = chroma_client.create_collection(
        name=collection_name,
        metadata={"description": "APSC 142 exam questions with embeddings"}
    )
    
    # Process each exam and question
    current_date = datetime.now()
    total_questions = 0
    
    for exam_idx, exam in enumerate(exams):
        print(f"\nProcessing exam {exam_idx + 1}/{len(exams)}: {exam.exam_metadata.date}")
        
        exam_total_marks = exam.get_total_marks()
        
        for q_idx, question in enumerate(exam.questions):
            # Create text representation for embedding
            text_parts = [
                f"Section: {question.section}",
                f"Question: {question.text}",
            ]
            
            if question.content_description:
                text_parts.append(f"Description: {question.content_description}")
            
            if question.answer_choices:
                text_parts.append(f"Choices: {' '.join(question.answer_choices)}")
            
            embedding_text = " | ".join(text_parts)
            
            # Calculate relevance score
            relevance = calculate_relevance_score(exam, question, current_date)
            
            # Create embedding
            print(f"  Embedding question {q_idx + 1}/{len(exam.questions)}...", end="\r")
            embedding = create_embedding(embedding_text)
            
            if not embedding:
                print(f"\n  Warning: Failed to create embedding for question {q_idx + 1}")
                continue
            
            # Create unique ID
            question_id = f"exam_{exam_idx}_q_{q_idx}"
            
            # Metadata
            metadata = {
                "exam_date": exam.exam_metadata.date,
                "course": exam.exam_metadata.course,
                "section": question.section,
                "marks": str(question.marks),
                "exam_total_marks": str(exam_total_marks),
                "relevance_score": str(relevance),
                "question_number": question.question_number,
                "text": question.text[:200]  # First 200 chars for search
            }
            
            # Add to collection
            collection.add(
                ids=[question_id],
                embeddings=[embedding],
                documents=[embedding_text],
                metadatas=[metadata]
            )
            
            total_questions += 1
        
        print(f"\n  Processed {len(exam.questions)} questions from this exam")
    
    print(f"\n{'='*60}")
    print(f"Ingestion complete!")
    print(f"Total questions embedded: {total_questions}")
    print(f"Collection: {collection_name}")
    print(f"{'='*60}")


if __name__ == "__main__":
    # Get project root (exam-generator directory)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    json_path = project_root / "data" / "question_bank.json"
    
    if not json_path.exists():
        print(f"Error: Question bank not found at {json_path}")
        exit(1)
    
    ingest_to_vector_db(str(json_path))

