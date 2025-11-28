"""
LLM calls for exam generation with prompt engineering.
Generates questions and full exams using OpenAI API.
"""

import os
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from openai import OpenAI
from models import (
    ExamGenerationRequest,
    GeneratedQuestion,
    GeneratedExam,
    ExamMetadata,
    Question
)

# Load environment variables
load_dotenv(encoding='utf-8')
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY").strip() if os.getenv("OPENAI_API_KEY") else None)


class ExamGenerator:
    """Generates exam questions and full exams using LLM."""
    
    def __init__(self, retriever=None):
        """Initialize generator with optional retriever for style examples."""
        self.retriever = retriever
    
    def generate_question(
        self,
        section: str,
        marks: int,
        style_examples: List[Dict[str, Any]] = None,
        difficulty: str = "medium"
    ) -> Optional[GeneratedQuestion]:
        """
        Generate a single question using LLM.
        
        Args:
            section: Question section/topic
            marks: Points for this question
            style_examples: List of example questions for style reference
            difficulty: Target difficulty level
        
        Returns:
            GeneratedQuestion or None if generation fails
        """
        # Build system prompt
        system_prompt = """You are an expert at creating programming exam questions for APSC 142 (Introduction to Computer Programming for Engineers).

Your questions should:
- Be clear and unambiguous
- Test understanding of programming concepts
- Be appropriate for first-year engineering students
- Include specific requirements and expected outputs
- Match the style and format of the provided examples"""

        # Build user prompt with examples
        user_prompt_parts = [
            f"Generate a {difficulty} difficulty programming question for the section: {section}",
            f"The question should be worth {marks} marks.",
            "",
            "Requirements:",
            "- The question should be clear and test practical programming skills",
            "- Include specific input/output examples if applicable",
            "- Specify any constraints or requirements",
            "- Format it similar to the examples below"
        ]
        
        # Add style examples
        if style_examples:
            user_prompt_parts.append("\nExample questions (match this style):")
            for i, example in enumerate(style_examples[:3], 1):  # Use top 3 examples
                user_prompt_parts.append(f"\nExample {i}:")
                user_prompt_parts.append(f"Section: {example.get('section', 'N/A')}")
                user_prompt_parts.append(f"Marks: {example.get('marks', 'N/A')}")
                user_prompt_parts.append(f"Text: {example.get('text', 'N/A')[:300]}")
        
        user_prompt_parts.append("\nGenerate the question in this format:")
        user_prompt_parts.append("Section: [section name]")
        user_prompt_parts.append("Marks: [number]")
        user_prompt_parts.append("Text: [question text]")
        
        user_prompt = "\n".join(user_prompt_parts)
        
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            # Parse response
            response_text = response.choices[0].message.content
            
            # Extract question details (simple parsing)
            question_text = response_text
            if "Text:" in response_text:
                question_text = response_text.split("Text:")[-1].strip()
            elif "text:" in response_text:
                question_text = response_text.split("text:")[-1].strip()
            
            return GeneratedQuestion(
                question_number="",  # Will be assigned later
                section=section,
                marks=marks,
                text=question_text.strip(),
                answer_choices=None
            )
            
        except Exception as e:
            print(f"Error generating question: {e}")
            return None
    
    def generate_exam(
        self,
        request: ExamGenerationRequest,
        style_examples: List[Dict[str, Any]] = None
    ) -> Optional[GeneratedExam]:
        """
        Generate a complete exam.
        
        Args:
            request: Exam generation parameters
            style_examples: Style examples from retriever
        
        Returns:
            GeneratedExam or None if generation fails
        """
        print(f"\nGenerating exam with {request.target_marks} total marks...")
        print(f"Difficulty: {request.difficulty}")
        
        # Determine question distribution
        if request.num_questions:
            num_questions = request.num_questions
        else:
            # Estimate based on target marks (assume avg 15 marks per question)
            num_questions = max(5, request.target_marks // 15)
        
        # Get sections
        sections = request.sections
        if not sections and self.retriever:
            # Get available sections from retriever
            section_stats = self.retriever.get_section_statistics()
            sections = list(section_stats.keys())[:5]  # Use top 5 sections
        
        if not sections:
            sections = ["Program Comprehension", "Computation and Output", "Arrays", "Functions"]
        
        # Distribute marks across questions
        marks_per_question = request.target_marks // num_questions
        remainder = request.target_marks % num_questions
        
        questions = []
        section_index = 0
        
        for i in range(num_questions):
            # Assign section (rotate through available sections)
            section = sections[section_index % len(sections)]
            section_index += 1
            
            # Assign marks (distribute remainder to first questions)
            marks = marks_per_question + (1 if i < remainder else 0)
            
            print(f"  Generating question {i+1}/{num_questions} ({section}, {marks} marks)...")
            
            # Get style examples for this section
            section_examples = None
            if style_examples:
                section_examples = [ex for ex in style_examples if ex.get('section') == section]
                if not section_examples:
                    section_examples = style_examples[:2]  # Fallback to general examples
            
            # Generate question
            question = self.generate_question(
                section=section,
                marks=marks,
                style_examples=section_examples,
                difficulty=request.difficulty
            )
            
            if question:
                question.question_number = str(i + 1)
                questions.append(question)
            else:
                print(f"    Warning: Failed to generate question {i+1}")
        
        if not questions:
            print("Error: Failed to generate any questions")
            return None
        
        # Create exam metadata
        exam_metadata = ExamMetadata(
            university="Queen's University",
            faculty="Faculty of Engineering & Applied Science",
            course=request.course,
            date="Generated",
            duration="3 hours"
        )
        
        return GeneratedExam(
            exam_metadata=exam_metadata,
            questions=questions
        )

