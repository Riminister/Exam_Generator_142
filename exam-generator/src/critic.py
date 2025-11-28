"""
Logic to evaluate generated questions.
Provides feedback and quality scores.
"""

from typing import List, Dict, Any, Optional
from openai import OpenAI
import os
from dotenv import load_dotenv

# Handle both relative and absolute imports
try:
    from .models import GeneratedQuestion, GeneratedExam, Question
except ImportError:
    # When running as script directly
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    from models import GeneratedQuestion, GeneratedExam, Question

# Load environment variables
load_dotenv(encoding='utf-8')
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY").strip() if os.getenv("OPENAI_API_KEY") else None)


class QuestionCritic:
    """Evaluates generated questions for quality and appropriateness."""
    
    def __init__(self):
        """Initialize critic."""
        pass
    
    def evaluate_question(
        self,
        question: GeneratedQuestion,
        reference_questions: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Evaluate a single question.
        
        Returns:
            Dictionary with scores and feedback
        """
        # Build evaluation prompt
        system_prompt = """You are an expert at evaluating programming exam questions. 
Evaluate questions based on:
1. Clarity and understandability
2. Appropriateness for first-year engineering students
3. Alignment with APSC 142 course content
4. Specificity and testability
5. Style consistency with reference examples"""

        user_prompt_parts = [
            "Evaluate this exam question:",
            f"Section: {question.section}",
            f"Text: {question.text}",
            "",
            "Provide:",
            "1. Overall quality score (0-10)",
            "2. Specific feedback on what works well",
            "3. Specific suggestions for improvement",
            "4. Whether the question is appropriate for first-year engineering students"
        ]
        
        if reference_questions:
            user_prompt_parts.append("\nReference questions for style comparison:")
            for i, ref in enumerate(reference_questions[:2], 1):
                user_prompt_parts.append(f"\nReference {i}:")
                user_prompt_parts.append(f"  {ref.get('text', '')[:200]}")
        
        user_prompt = "\n".join(user_prompt_parts)
        
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=400
            )
            
            evaluation_text = response.choices[0].message.content
            
            # Extract score (improved parsing)
            score = 7.0  # Default
            try:
                import re
                # Look for patterns like "8/10", "score: 8", "8 out of 10", "Overall quality score: 8"
                # Try to find the first number that appears to be a score
                patterns = [
                    r'(?:score|quality|rating)[:\s]+(\d+(?:\.\d+)?)\s*(?:/|out of)\s*10',  # "score: 8/10"
                    r'(\d+(?:\.\d+)?)\s*/?\s*10',  # "8/10" or "8 10"
                    r'(?:Overall|Quality|Score)[:\s]+(\d+(?:\.\d+)?)',  # "Overall: 8"
                    r'(\d+(?:\.\d+)?)\s*(?:out of|/)\s*10',  # "8 out of 10"
                ]
                
                for pattern in patterns:
                    matches = re.findall(pattern, evaluation_text, re.IGNORECASE)
                    if matches:
                        potential_score = float(matches[0])
                        if 0 <= potential_score <= 10:
                            score = potential_score
                            break
            except Exception as e:
                print(f"Warning: Could not parse score from evaluation: {e}")
                score = 7.0  # Default fallback
            
            return {
                "score": score,
                "feedback": evaluation_text,
                "approved": score >= 7.0,  # Threshold for approval
                "question": question
            }
            
        except Exception as e:
            print(f"Error evaluating question: {e}")
            return {
                "score": 5.0,
                "feedback": f"Evaluation error: {str(e)}",
                "approved": False,
                "question": question
            }
    
    def evaluate_exam(
        self,
        exam: GeneratedExam,
        reference_questions: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Evaluate a complete exam.
        
        Returns:
            Dictionary with overall scores and per-question evaluations
        """
        print("\nEvaluating generated exam...")
        
        question_evaluations = []
        total_score = 0.0
        
        for question in exam.questions:
            print(f"  Evaluating question {question.question_number}...")
            evaluation = self.evaluate_question(question, reference_questions)
            question_evaluations.append(evaluation)
            total_score += evaluation["score"]
        
        avg_score = total_score / len(question_evaluations) if question_evaluations else 0.0
        
        # Overall exam evaluation
        approved_count = sum(1 for e in question_evaluations if e["approved"])
        approval_rate = approved_count / len(question_evaluations) if question_evaluations else 0.0
        
        # Check mark distribution
        total_marks = sum(q.marks for q in exam.questions)
        mark_distribution_ok = abs(total_marks - 100) <= 10  # Within 10 marks of target
        
        return {
            "overall_score": avg_score,
            "approval_rate": approval_rate,
            "approved_questions": approved_count,
            "total_questions": len(exam.questions),
            "mark_distribution_ok": mark_distribution_ok,
            "total_marks": total_marks,
            "question_evaluations": question_evaluations,
            "exam_approved": approval_rate >= 0.7 and mark_distribution_ok
        }
    
    def provide_feedback(
        self,
        evaluation: Dict[str, Any]
    ) -> str:
        """Generate human-readable feedback from evaluation."""
        feedback_parts = [
            f"Overall Score: {evaluation['overall_score']:.1f}/10",
            f"Approval Rate: {evaluation['approval_rate']*100:.1f}%",
            f"Approved Questions: {evaluation['approved_questions']}/{evaluation['total_questions']}",
            f"Total Marks: {evaluation['total_marks']}",
            ""
        ]
        
        if evaluation['exam_approved']:
            feedback_parts.append("✓ Exam is APPROVED and ready for use")
        else:
            feedback_parts.append("✗ Exam needs improvements before use")
            if evaluation['approval_rate'] < 0.7:
                feedback_parts.append("  - Too many questions need improvement")
            if not evaluation['mark_distribution_ok']:
                feedback_parts.append("  - Mark distribution needs adjustment")
        
        feedback_parts.append("\nPer-question feedback:")
        for i, q_eval in enumerate(evaluation['question_evaluations'], 1):
            status = "✓" if q_eval['approved'] else "✗"
            feedback_parts.append(f"\n{status} Question {i} (Score: {q_eval['score']:.1f}/10):")
            feedback_parts.append(f"  {q_eval['feedback'][:200]}...")
        
        return "\n".join(feedback_parts)

