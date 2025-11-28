"""
LLM calls for exam generation with prompt engineering.
Generates questions and full exams using OpenAI API.
"""

import os
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from openai import OpenAI

# Handle both relative and absolute imports
try:
    from .models import (
        ExamGenerationRequest,
        GeneratedQuestion,
        GeneratedExam,
        ExamMetadata,
        Question
    )
except ImportError:
    # When running as script directly
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
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
    
    def _get_section_description(self, section: str) -> str:
        """Get description of what a section focuses on."""
        descriptions = {
            "Program Comprehension": "reading and understanding existing code, identifying bugs, tracing execution",
            "Computation and Output": "mathematical calculations, formulas, numerical methods, output formatting",
            "1D Arrays": "one-dimensional arrays, array manipulation, indexing, array algorithms",
            "2D Arrays": "two-dimensional arrays, matrix operations, nested loops with arrays",
            "Functions": "function definition, parameters, return values, function calls, modular programming",
            "Algorithms": "algorithm design, sorting, searching, algorithmic thinking",
            "Robot Programming": "robot control, sensors, actuators, robot logic and movement",
            "1-D Arrays": "one-dimensional arrays, array manipulation, indexing, array algorithms",
            "2-D Arrays": "two-dimensional arrays, matrix operations, nested loops with arrays",
            "Function and 1D Arrays": "combining functions with array operations",
            "Functions and 1-D Arrays": "combining functions with array operations",
            "2D Array and Function": "combining 2D arrays with functions",
            "Computation and Numerical Methods": "mathematical computations, numerical analysis, calculations",
            "Design Thinking": "problem-solving approach, algorithm design, program structure",
            "Algorithms: Sorting and Searching": "sorting algorithms, searching algorithms, algorithm efficiency",
            "Simulating a Physical Problem": "modeling physical systems, simulation programming",
            "NXT Robot Operation": "LEGO NXT robot programming, sensor integration",
            "Robot Operation": "robot control, sensors, actuators, robot logic"
        }
        return descriptions.get(section, f"programming concepts related to {section}")
    
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
        # Build system prompt with strong section enforcement
        system_prompt = f"""You are an expert at creating programming exam questions for APSC 142 (Introduction to Computer Programming for Engineers).

CRITICAL: You MUST create a question for the "{section}" section. Do NOT create a "Program Comprehension" question unless explicitly told to.

Section-specific requirements:
- "{section}" questions should focus on {self._get_section_description(section)}
- The question MUST test concepts specific to {section}
- Do NOT default to program comprehension/reading code questions

Your questions should:
- Be clear and unambiguous
- Test understanding of programming concepts specific to {section}
- Be appropriate for first-year engineering students
- Include specific input/output examples if applicable
- Match the style and format of the provided examples"""

        # Build user prompt with examples
        section_desc = self._get_section_description(section)
        
        user_prompt_parts = [
            f"CRITICAL INSTRUCTION: Generate a {difficulty} difficulty question for the '{section}' section.",
            f"The question MUST be about {section_desc}.",
            f"DO NOT create a 'Program Comprehension' question. This MUST be a '{section}' question.",
            f"The question should be worth {marks} marks.",
            "",
            f"Section '{section}' focuses on: {section_desc}",
            "",
            "Requirements:",
            f"- The question MUST test {section} concepts, NOT program reading/comprehension",
            "- Be clear and test practical programming skills",
            "- Include specific input/output examples if applicable",
            "- Specify any constraints or requirements",
            "- Format it similar to the examples below",
            f"- The question content must clearly demonstrate {section} knowledge"
        ]
        
        # Add style examples - emphasize section-specific examples
        if style_examples:
            # Filter to show section-specific examples first
            section_specific = [ex for ex in style_examples if ex.get('section') == section]
            other_examples = [ex for ex in style_examples if ex.get('section') != section]
            
            if section_specific:
                user_prompt_parts.append(f"\nExample questions from '{section}' section (match this style and topic):")
                for i, example in enumerate(section_specific[:3], 1):
                    user_prompt_parts.append(f"\nExample {i} (Section: {example.get('section', 'N/A')}):")
                    user_prompt_parts.append(f"Marks: {example.get('marks', 'N/A')}")
                    example_text = example.get('text', 'N/A')
                    if len(example_text) > 400:
                        example_text = example_text[:400] + "..."
                    user_prompt_parts.append(f"Text: {example_text}")
                    user_prompt_parts.append(f"  ^ This is a '{section}' question - your question should be similar!")
            
            # Also show one example from a different section to contrast
            if other_examples and len(section_specific) < 2:
                user_prompt_parts.append(f"\nExample from different section (for contrast - DO NOT follow this style):")
                example = other_examples[0]
                user_prompt_parts.append(f"Section: {example.get('section', 'N/A')} (NOT '{section}')")
                user_prompt_parts.append(f"Text: {example.get('text', 'N/A')[:200]}...")
                user_prompt_parts.append(f"  ^ This is NOT a '{section}' question - do NOT create this type!")
        
        user_prompt_parts.append("\nGenerate the question in this format:")
        user_prompt_parts.append("Section: [section name]")
        user_prompt_parts.append("Marks: [number]")
        user_prompt_parts.append("Text: [question text]")
        
        user_prompt = "\n".join(user_prompt_parts)
        
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
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
            
            # Clean up the text - remove any section labels that might have been included
            question_text = question_text.strip()
            # Remove any "Section: X" prefixes
            if question_text.startswith("Section:"):
                question_text = question_text.split("\n", 1)[-1].strip()
            if question_text.startswith("section:"):
                question_text = question_text.split("\n", 1)[-1].strip()
            
            return GeneratedQuestion(
                question_number="",  # Will be assigned later
                section=section,  # Use the section we specified, not what LLM might have said
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
        
        # Get sections - ensure diversity
        sections = request.sections
        if not sections and self.retriever:
            # Get available sections from retriever, prioritize diverse sections
            section_stats = self.retriever.get_section_statistics()
            # Sort by count to get most common sections, but ensure we have diversity
            sorted_sections = sorted(section_stats.items(), key=lambda x: x[1], reverse=True)
            sections = [s[0] for s in sorted_sections[:min(8, len(sorted_sections))]]  # Get up to 8 sections
        
        if not sections:
            # Default diverse sections based on actual question bank
            sections = [
                "Program Comprehension",
                "Computation and Output", 
                "1D Arrays",
                "2D Arrays",
                "Functions",
                "Algorithms",
                "Robot Programming"
            ]
        
        print(f"Using sections: {sections}")
        
        # Distribute marks across questions
        marks_per_question = request.target_marks // num_questions
        remainder = request.target_marks % num_questions
        
        questions = []
        section_index = 0
        
        # Ensure we use different sections - distribute evenly
        questions_per_section = num_questions // len(sections)
        section_assignments = []
        for section in sections:
            section_assignments.extend([section] * questions_per_section)
        # Add remaining questions to first sections
        for i in range(num_questions % len(sections)):
            section_assignments.append(sections[i])
        
        for i in range(num_questions):
            # Assign section (ensuring diversity)
            section = section_assignments[i] if i < len(section_assignments) else sections[section_index % len(sections)]
            section_index += 1
            
            # Assign marks (distribute remainder to first questions)
            marks = marks_per_question + (1 if i < remainder else 0)
            
            print(f"  Generating question {i+1}/{num_questions} ({section}, {marks} marks)...")
            
            # Get style examples for this section - CRITICAL: prioritize examples from THIS section
            section_examples = None
            if style_examples:
                # STRONGLY prioritize examples from this specific section
                section_examples = [ex for ex in style_examples if ex.get('section') == section]
                
                # If we have examples from this section, use them exclusively
                if len(section_examples) >= 2:
                    section_examples = section_examples[:3]  # Use up to 3 from this section
                    print(f"    Using {len(section_examples)} examples from '{section}' section")
                else:
                    # If not enough from this section, try to get more from retriever
                    if self.retriever:
                        print(f"    Retrieving more examples for '{section}' section...")
                        additional = self.retriever.retrieve_style_examples(
                            section=section,
                            n_examples=3,
                            difficulty=request.difficulty,
                            ensure_diversity=False  # Get from this section only
                        )
                        if additional:
                            section_examples.extend(additional)
                            section_examples = section_examples[:3]
                    
                    # Last resort: use general examples but emphasize the section
                    if not section_examples or len(section_examples) < 2:
                        print(f"    Warning: Limited examples for '{section}', using general examples")
                        section_examples = style_examples[:2] if style_examples else None
            
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

