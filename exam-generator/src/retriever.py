"""
Logic to fetch "style examples" from vector database.
Retrieves similar questions based on semantic search.
"""

import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any
from openai import OpenAI
import os
from dotenv import load_dotenv
from .models import Question, ExamMetadata

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


class QuestionRetriever:
    """Retrieves style examples from vector database."""
    
    def __init__(self, collection_name: str = "exam_questions"):
        """Initialize retriever with ChromaDB collection."""
        from pathlib import Path
        script_dir = Path(__file__).parent
        project_root = script_dir.parent
        db_path = project_root / "chroma_db"
        
        self.chroma_client = chromadb.PersistentClient(
            path=str(db_path),
            settings=Settings(anonymized_telemetry=False)
        )
        
        try:
            self.collection = self.chroma_client.get_collection(name=collection_name)
        except Exception as e:
            raise Exception(f"Collection '{collection_name}' not found. Run ingest.py first. Error: {e}")
    
    def retrieve_by_query(
        self,
        query: str,
        n_results: int = 5,
        section_filter: str = None,
        min_relevance: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Retrieve questions similar to the query.
        
        Args:
            query: Text query to find similar questions
            n_results: Number of results to return
            section_filter: Optional section to filter by
            min_relevance: Minimum relevance score threshold
        
        Returns:
            List of question dictionaries with metadata
        """
        # Create embedding for query
        query_embedding = create_embedding(query)
        
        if not query_embedding:
            return []
        
        # Build where clause for filtering
        where = {}
        if section_filter:
            where["section"] = section_filter
        
        # Query collection
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where if where else None
            )
        except Exception as e:
            print(f"Error querying collection: {e}")
            return []
        
        # Format results
        retrieved_questions = []
        
        if results['ids'] and len(results['ids'][0]) > 0:
            for i in range(len(results['ids'][0])):
                metadata = results['metadatas'][0][i]
                document = results['documents'][0][i]
                
                # Check relevance score
                relevance = float(metadata.get('relevance_score', 0.0))
                if relevance < min_relevance:
                    continue
                
                retrieved_questions.append({
                    "id": results['ids'][0][i],
                    "text": metadata.get('text', ''),
                    "section": metadata.get('section', ''),
                    "marks": int(metadata.get('marks', 0)),
                    "exam_date": metadata.get('exam_date', ''),
                    "course": metadata.get('course', ''),
                    "question_number": metadata.get('question_number', ''),
                    "document": document,
                    "relevance_score": relevance,
                    "distance": results['distances'][0][i] if 'distances' in results else None
                })
        
        return retrieved_questions
    
    def retrieve_style_examples(
        self,
        section: str = None,
        n_examples: int = 5,
        difficulty: str = "medium"
    ) -> List[Dict[str, Any]]:
        """
        Retrieve style examples for exam generation.
        
        Args:
            section: Optional section to filter by
            n_examples: Number of examples to retrieve
            difficulty: Target difficulty (easy, medium, hard)
        
        Returns:
            List of example questions
        """
        # Build query based on difficulty and section
        query_parts = []
        
        if section:
            query_parts.append(f"Section: {section}")
        
        # Add difficulty context
        if difficulty == "easy":
            query_parts.append("simple basic programming question")
        elif difficulty == "hard":
            query_parts.append("complex advanced programming question")
        else:
            query_parts.append("programming question")
        
        query = " | ".join(query_parts) if query_parts else "programming exam question"
        
        # Retrieve questions
        results = self.retrieve_by_query(
            query=query,
            n_results=n_examples * 2,  # Get more to filter by difficulty
            section_filter=section
        )
        
        # Filter and sort by relevance
        filtered_results = sorted(
            results,
            key=lambda x: x['relevance_score'],
            reverse=True
        )[:n_examples]
        
        return filtered_results
    
    def get_section_statistics(self) -> Dict[str, int]:
        """Get statistics about available sections."""
        # Get all items to analyze sections
        all_items = self.collection.get()
        
        section_counts = {}
        for metadata in all_items['metadatas']:
            section = metadata.get('section', 'Unknown')
            section_counts[section] = section_counts.get(section, 0) + 1
        
        return section_counts

