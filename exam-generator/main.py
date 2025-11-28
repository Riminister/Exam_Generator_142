"""
Main entry point for exam generation.
Implements the feedback loop: Generate -> Evaluate -> Refine
"""

import json
import argparse
from pathlib import Path
from typing import Optional

from src.models import ExamGenerationRequest, GeneratedExam
from src.retriever import QuestionRetriever
from src.generator import ExamGenerator
from src.critic import QuestionCritic


def main():
    """Main function for exam generation with feedback loop."""
    parser = argparse.ArgumentParser(description="Generate APSC 142 exam questions")
    parser.add_argument("--marks", type=int, default=100, help="Target total marks")
    parser.add_argument("--difficulty", type=str, default="medium", choices=["easy", "medium", "hard"])
    parser.add_argument("--num-questions", type=int, help="Number of questions (auto-calculated if not specified)")
    parser.add_argument("--sections", nargs="+", help="Specific sections to include")
    parser.add_argument("--style-examples", type=int, default=5, help="Number of style examples to retrieve")
    parser.add_argument("--iterations", type=int, default=2, help="Number of feedback loop iterations")
    parser.add_argument("--output", type=str, default="output/new_exam_v1.json", help="Output file path")
    
    args = parser.parse_args()
    
    print("="*60)
    print("APSC 142 Exam Generator")
    print("="*60)
    
    # Initialize components
    print("\nInitializing components...")
    try:
        retriever = QuestionRetriever()
        print("✓ Vector database connected")
    except Exception as e:
        print(f"✗ Error connecting to vector database: {e}")
        print("  Run 'python src/ingest.py' first to create the database")
        retriever = None
    
    generator = ExamGenerator(retriever=retriever)
    critic = QuestionCritic()
    
    # Create generation request
    request = ExamGenerationRequest(
        target_marks=args.marks,
        difficulty=args.difficulty,
        num_questions=args.num_questions,
        sections=args.sections,
        style_examples_count=args.style_examples
    )
    
    # Retrieve style examples
    style_examples = None
    if retriever:
        print(f"\nRetrieving {args.style_examples} style examples...")
        style_examples = retriever.retrieve_style_examples(
            section=None,
            n_examples=args.style_examples,
            difficulty=args.difficulty
        )
        print(f"✓ Retrieved {len(style_examples)} examples")
    
    # Feedback loop: Generate -> Evaluate -> Refine
    best_exam: Optional[GeneratedExam] = None
    best_score = 0.0
    
    for iteration in range(args.iterations):
        print(f"\n{'='*60}")
        print(f"Iteration {iteration + 1}/{args.iterations}")
        print(f"{'='*60}")
        
        # Generate exam
        print("\n[Step 1] Generating exam...")
        exam = generator.generate_exam(request, style_examples)
        
        if not exam:
            print("✗ Failed to generate exam")
            continue
        
        print(f"✓ Generated {len(exam.questions)} questions")
        
        # Evaluate exam
        print("\n[Step 2] Evaluating exam...")
        evaluation = critic.evaluate_exam(exam, style_examples)
        
        # Display feedback
        feedback = critic.provide_feedback(evaluation)
        print("\n" + feedback)
        
        # Track best exam
        if evaluation['overall_score'] > best_score:
            best_score = evaluation['overall_score']
            best_exam = exam
        
        # If approved, we can stop early
        if evaluation['exam_approved']:
            print("\n✓ Exam approved! Stopping early.")
            best_exam = exam
            break
        
        # If not last iteration, provide refinement guidance
        if iteration < args.iterations - 1:
            print("\n[Step 3] Refining for next iteration...")
            # Could add logic here to adjust request based on feedback
            # For now, we'll just regenerate with same parameters
    
    # Save best exam
    if best_exam:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to standard Exam format and save
        exam_dict = best_exam.model_dump()
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(exam_dict, f, indent=2, ensure_ascii=False)
        
        print(f"\n{'='*60}")
        print(f"✓ Exam saved to: {output_path}")
        print(f"  Total questions: {len(best_exam.questions)}")
        print(f"  Total marks: {sum(q.marks for q in best_exam.questions)}")
        print(f"  Best score: {best_score:.1f}/10")
        print(f"{'='*60}")
    else:
        print("\n✗ Failed to generate a valid exam")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())

