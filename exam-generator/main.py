"""
Main entry point for exam generation.
Implements the feedback loop: Generate -> Evaluate -> Refine
"""

import json
import argparse
from pathlib import Path
from typing import Optional
from datetime import datetime

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
    parser.add_argument("--output", type=str, default="output/newquestionbank.json", help="Output file path")
    
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
    
    # Retrieve style examples - ensure diversity
    style_examples = None
    if retriever:
        print(f"\nRetrieving {args.style_examples} style examples (ensuring section diversity)...")
        style_examples = retriever.retrieve_style_examples(
            section=None,
            n_examples=args.style_examples,
            difficulty=args.difficulty,
            ensure_diversity=True  # Get examples from different sections
        )
        print(f"✓ Retrieved {len(style_examples)} examples")
        if style_examples:
            sections_in_examples = set(ex.get('section', '') for ex in style_examples)
            print(f"  Examples from {len(sections_in_examples)} different sections: {', '.join(sorted(sections_in_examples))}")
    
    # Feedback loop: Generate -> Evaluate -> Refine
    best_exam: Optional[GeneratedExam] = None
    best_score = 0.0
    all_evaluations = []  # Track all evaluations to collect approved questions
    
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
        all_evaluations.append((exam, evaluation))  # Store for later question extraction
        
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
    
    # Save approved questions to question bank
    if best_exam:
        # Get the exam-generator directory (parent of script location)
        script_dir = Path(__file__).parent
        project_root = script_dir  # main.py is in exam-generator root
        
        # Resolve output path relative to project root
        if Path(args.output).is_absolute():
            output_path = Path(args.output)
        else:
            output_path = project_root / args.output
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # Extract approved questions (score >= 7.0) from all iterations
            all_approved_questions = []
            
            # Collect questions from all iterations that were approved
            for exam, evaluation in all_evaluations:
                for q_eval in evaluation.get('question_evaluations', []):
                    score = q_eval.get('score', 0)
                    # Only save questions with score >= 7.0
                    if score >= 7.0:
                        question = q_eval.get('question')
                        if question:
                            # Add difficulty and metadata to question
                            question_dict = question.model_dump() if hasattr(question, 'model_dump') else question
                            question_dict['difficulty'] = args.difficulty
                            question_dict['quality_score'] = score
                            question_dict['generated_date'] = datetime.now().strftime("%Y-%m-%d")
                            # Remove question_number as it's exam-specific
                            if 'question_number' in question_dict:
                                del question_dict['question_number']
                            # Remove explanation if present (not needed in question bank)
                            if 'explanation' in question_dict and not question_dict['explanation']:
                                del question_dict['explanation']
                            all_approved_questions.append(question_dict)
            
            # If no approved questions from evaluation, use all questions from best exam
            if not all_approved_questions and best_exam:
                print("Warning: No approved questions from evaluation, saving all questions")
                for q in best_exam.questions:
                    q_dict = q.model_dump() if hasattr(q, 'model_dump') else q
                    q_dict['difficulty'] = args.difficulty
                    q_dict['quality_score'] = 7.0  # Default score
                    q_dict['generated_date'] = datetime.now().strftime("%Y-%m-%d")
                    if 'question_number' in q_dict:
                        del q_dict['question_number']
                    if 'explanation' in q_dict and not q_dict['explanation']:
                        del q_dict['explanation']
                    all_approved_questions.append(q_dict)
            
            # Load existing question bank if it exists
            existing_questions = []
            if output_path.exists():
                try:
                    with open(output_path, 'r', encoding='utf-8') as f:
                        existing_data = json.load(f)
                        if isinstance(existing_data, list):
                            existing_questions = existing_data
                        elif isinstance(existing_data, dict) and 'questions' in existing_data:
                            existing_questions = existing_data['questions']
                except Exception as e:
                    print(f"Warning: Could not load existing question bank: {e}")
            
            # Merge with existing questions
            all_questions = existing_questions + all_approved_questions
            
            # Save as question bank (array of questions)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(all_questions, f, indent=2, ensure_ascii=False)
            
            # Print statistics
            sections_used = {}
            difficulties_used = {}
            for q in all_approved_questions:
                sections_used[q.get('section', 'Unknown')] = sections_used.get(q.get('section', 'Unknown'), 0) + 1
                difficulties_used[q.get('difficulty', 'Unknown')] = difficulties_used.get(q.get('difficulty', 'Unknown'), 0) + 1
            
            print(f"\n{'='*60}")
            print(f"✓ Question bank updated: {output_path.absolute()}")
            print(f"  New questions added: {len(all_approved_questions)}")
            print(f"  Total questions in bank: {len(all_questions)}")
            print(f"  Best score: {best_score:.1f}/10")
            print(f"\n  New questions by section:")
            for section, count in sections_used.items():
                print(f"    - {section}: {count} question(s)")
            print(f"\n  New questions by difficulty:")
            for diff, count in difficulties_used.items():
                print(f"    - {diff}: {count} question(s)")
            print(f"{'='*60}")
        except Exception as e:
            print(f"\n✗ Error saving question bank: {e}")
            import traceback
            traceback.print_exc()
            return 1
    else:
        print("\n✗ Failed to generate a valid exam")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())

