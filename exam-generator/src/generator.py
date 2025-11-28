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
    
    def _normalize_section_name(self, section: str) -> str:
        """Normalize section names to handle variations."""
        if not section:
            return ""
        # Normalize common variations
        normalized = section.strip()
        # Handle array variations
        if "1D Array" in normalized or "1-D Array" in normalized:
            return "1D Arrays"
        if "2D Array" in normalized or "2-D Array" in normalized:
            return "2D Arrays"
        # Handle function variations
        if "Function" in normalized and "Array" in normalized:
            return "Functions and Arrays"
        return normalized
    
    def _are_sections_related(self, section1: str, section2: str) -> bool:
        """Check if two sections are related (e.g., both array-related)."""
        array_keywords = ["array", "arrays"]
        function_keywords = ["function", "functions"]
        
        s1_lower = section1.lower()
        s2_lower = section2.lower()
        
        # Both are array-related
        if any(kw in s1_lower for kw in array_keywords) and any(kw in s2_lower for kw in array_keywords):
            return True
        # Both are function-related
        if any(kw in s1_lower for kw in function_keywords) and any(kw in s2_lower for kw in function_keywords):
            return True
        return False
    
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
        style_examples: List[Dict[str, Any]] = None,
        difficulty: str = "medium"
    ) -> Optional[GeneratedQuestion]:
        """
        Generate a single question using LLM.
        
        Args:
            section: Question section/topic
            style_examples: List of example questions for style reference
            difficulty: Target difficulty level (easy/medium/hard)
        
        Returns:
            GeneratedQuestion
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
            f"DO NOT create a 'Program Comprehension' question unless section is 'Program Comprehension'.",
            "",
            f"Section '{section}' focuses on: {section_desc}",
            "",
            "Requirements:",
            f"- The question MUST test {section} concepts",
            "- Be ORIGINAL and DIFFERENT from the reference examples (different topic/scenario)",
            "- Be clear and test practical programming skills",
            "- Include specific input/output examples if applicable",
            "- Specify any constraints or requirements",
            "- Match the STYLE and FORMAT of examples, but use DIFFERENT content/topic",
            f"- The question content must clearly demonstrate {section} knowledge",
            f"- Match the difficulty level ({difficulty}) of the reference examples",
            "- Be creative and avoid repeating topics from the examples"
        ]
        
        # Add style examples - use diverse examples to encourage variation
        if style_examples:
            # Normalize section names for matching (handle variations like "1D Array" vs "1D Arrays")
            normalized_section = self._normalize_section_name(section)
            section_specific = []
            related_examples = []
            other_examples = []
            
            for ex in style_examples:
                ex_section = ex.get('section', '')
                ex_normalized = self._normalize_section_name(ex_section)
                if ex_normalized == normalized_section:
                    section_specific.append(ex)
                elif self._are_sections_related(normalized_section, ex_normalized):
                    related_examples.append(ex)
                else:
                    other_examples.append(ex)
            
            # Use diverse examples: 1-2 from section, 1-2 from related, 1 from other
            examples_to_show = []
            examples_to_show.extend(section_specific[:2])  # Up to 2 from exact section
            examples_to_show.extend(related_examples[:1])   # 1 from related section
            examples_to_show.extend(other_examples[:1])      # 1 from different section for contrast
            
            if examples_to_show:
                user_prompt_parts.append(f"\nReference examples (use these for STYLE only, create a DIFFERENT question):")
                for i, example in enumerate(examples_to_show[:4], 1):
                    user_prompt_parts.append(f"\nExample {i} (Section: {example.get('section', 'N/A')}):")
                    example_text = example.get('text', 'N/A')
                    if len(example_text) > 300:
                        example_text = example_text[:300] + "..."
                    user_prompt_parts.append(f"Text: {example_text}")
                
                user_prompt_parts.append(f"\nIMPORTANT: Your question must be:")
                user_prompt_parts.append(f"- In the '{section}' section")
                user_prompt_parts.append(f"- DIFFERENT from the examples above (different topic, different approach)")
                user_prompt_parts.append(f"- Similar in STYLE and FORMAT only, not content")
        
        user_prompt_parts.append("\nGenerate the question text only (do not include marks or section labels):")
        
        user_prompt = "\n".join(user_prompt_parts)
        
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.9,  # Increased for more diversity
                max_tokens=600  # Increased for longer, more detailed questions
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
                marks=0,
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

