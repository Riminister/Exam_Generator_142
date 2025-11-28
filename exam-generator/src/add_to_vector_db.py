"""
Add newly generated questions to the existing vector database.
This allows new questions to be used as style examples in future generations.
"""

import os
import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
import chromadb
from chromadb.config import Settings
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv(encoding='utf-8')
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY").strip() if os.getenv("OPENAI_API_KEY") else None)


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


def add_questions_to_vector_db(
    questions: List[Dict[str, Any]],
    collection_name: str = "exam_questions"
):
    """
    Add newly generated questions to the existing vector database.
    
    Args:
        questions: List of question dictionaries from newquestionbank.json
        collection_name: Name of the ChromaDB collection
    """
    if not questions:
        print("No questions to add")
        return
    
    # Initialize ChromaDB
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    db_path = project_root / "chroma_db"
    
    chroma_client = chromadb.PersistentClient(
        path=str(db_path),
        settings=Settings(anonymized_telemetry=False)
    )
    
    # Get existing collection
    try:
        collection = chroma_client.get_collection(name=collection_name)
        print(f"Found existing collection: {collection_name}")
    except Exception:
        print(f"Error: Collection '{collection_name}' not found. Run ingest.py first.")
        return
    
    # Get current count
    current_count = collection.count()
    print(f"Current questions in DB: {current_count}")
    
    # Process new questions
    added_count = 0
    current_date = datetime.now()
    
    for q_idx, question in enumerate(questions):
        # Skip if question doesn't have required fields
        if not question.get('text') or not question.get('section'):
            print(f"  Skipping question {q_idx + 1}: missing required fields")
            continue
        
        # Create text representation for embedding
        text_parts = [
            f"Section: {question.get('section', 'Unknown')}",
            f"Question: {question.get('text', '')}",
        ]
        
        if question.get('content_description'):
            text_parts.append(f"Description: {question.get('content_description')}")
        
        if question.get('answer_choices'):
            text_parts.append(f"Choices: {' '.join(question.get('answer_choices', []))}")
        
        embedding_text = " | ".join(text_parts)
        
        # Use relevance score (default 0.5 for generated questions)
        relevance_score = 0.5
        
        # Create embedding
        print(f"  Embedding question {q_idx + 1}/{len(questions)}...", end="\r")
        embedding = create_embedding(embedding_text)
        
        if not embedding:
            print(f"\n  Warning: Failed to create embedding for question {q_idx + 1}")
            continue
        
        # Create unique ID (use generated_date + index to avoid collisions)
        generated_date = question.get('generated_date', current_date.strftime("%Y-%m-%d"))
        question_id = f"generated_{generated_date}_{q_idx}_{current_count + added_count}"
        
        # Metadata
        metadata = {
            "exam_date": generated_date,
            "course": "APSC 142 - Introduction to Computer Programming for Engineers",
            "section": question.get('section', 'Unknown'),
            "marks": str(question.get('marks', 0)),  # Keep for backward compatibility
            "exam_total_marks": "0",  # Not applicable for generated questions
            "relevance_score": str(relevance_score),
            "question_number": str(q_idx + 1),
            "text": question.get('text', '')[:200],  # First 200 chars for search
            "difficulty": question.get('difficulty', 'medium'),
            "quality_score": str(question.get('quality_score', 7.0)),
            "is_generated": "true"  # Flag to identify generated questions
        }
        
        # Add to collection
        try:
            collection.add(
                ids=[question_id],
                embeddings=[embedding],
                documents=[embedding_text],
                metadatas=[metadata]
            )
            added_count += 1
        except Exception as e:
            print(f"\n  Warning: Could not add question {q_idx + 1}: {e}")
            continue
    
    print(f"\n  Processed {len(questions)} questions")
    print(f"\n{'='*60}")
    print(f"Added {added_count} new questions to vector database")
    print(f"Total questions in DB: {collection.count()}")
    print(f"{'='*60}")


def add_from_json(json_path: str, collection_name: str = "exam_questions"):
    """
    Load questions from JSON file and add to vector database.
    
    Args:
        json_path: Path to JSON file with questions (array format)
        collection_name: Name of the ChromaDB collection
    """
    # Load questions
    json_file = Path(json_path)
    if not json_file.exists():
        print(f"Error: File not found: {json_path}")
        return
    
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Handle different JSON formats
    if isinstance(data, list):
        questions = data
    elif isinstance(data, dict) and 'questions' in data:
        questions = data['questions']
    else:
        print("Error: Invalid JSON format. Expected array of questions or dict with 'questions' key.")
        return
    
    print(f"Loaded {len(questions)} questions from {json_path}")
    
    # Filter to only include generated questions (those with generated_date or quality_score)
    generated_questions = [
        q for q in questions 
        if q.get('generated_date') or q.get('quality_score')
    ]
    
    if not generated_questions:
        print("No generated questions found (questions need 'generated_date' or 'quality_score')")
        return
    
    print(f"Found {len(generated_questions)} generated questions to add")
    
    # Add to vector database
    add_questions_to_vector_db(generated_questions, collection_name)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Add generated questions to vector database")
    parser.add_argument("--file", type=str, default="output/newquestionbank.json", help="JSON file with questions")
    parser.add_argument("--collection", type=str, default="exam_questions", help="ChromaDB collection name")
    
    args = parser.parse_args()
    
    # Get project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    # Resolve file path
    if Path(args.file).is_absolute():
        json_path = Path(args.file)
    else:
        json_path = project_root / args.file
    
    add_from_json(str(json_path), args.collection)

