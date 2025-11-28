"""
Main entry point for exam generation.
Implements the feedback loop: Generate -> Evaluate -> Refine
"""

import json
import argparse
from pathlib import Path
from typing import Optional
from datetime import datetime

from src.models import GeneratedExam
from src.retriever import QuestionRetriever
from src.generator import ExamGenerator
from src.critic import QuestionCritic


def main():
    """Main function for exam generation with feedback loop."""
    parser = argparse.ArgumentParser(description="Generate APSC 142 exam questions")
    parser.add_argument("--difficulty", type=str, default="medium", choices=["easy", "medium", "hard"])
    parser.add_argument("--num-questions", type=int, default=10, help="Number of questions to generate")
    parser.add_argument("--sections", nargs="+", help="Specific sections to include (auto-selects if not specified)")
    parser.add_argument("--section", type=str, help="Generate questions for a single specific section")
    parser.add_argument("--style-examples", type=int, default=5, help="Number of style examples to retrieve")
    parser.add_argument("--min-score", type=float, default=7.0, help="Minimum quality score to save question (default: 7.0)")
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
    
    # Determine sections to use
    if args.section:
        # Single section specified
        sections_to_use = [args.section]
        print(f"\nGenerating questions for section: {args.section}")
    elif args.sections:
        # Multiple sections specified
        sections_to_use = args.sections
        print(f"\nGenerating questions for sections: {', '.join(sections_to_use)}")
    else:
        # Auto-select sections from database
        if retriever:
            section_stats = retriever.get_section_statistics()
            sorted_sections = sorted(section_stats.items(), key=lambda x: x[1], reverse=True)
            sections_to_use = [s[0] for s in sorted_sections[:8]]  # Top 8 sections
            print(f"\nAuto-selected sections: {', '.join(sections_to_use)}")
        else:
            # Default sections
            sections_to_use = [
                "Program Comprehension",
                "Computation and Output", 
                "1D Arrays",
                "2D Arrays",
                "Functions",
                "Algorithms"
            ]
            print(f"\nUsing default sections: {', '.join(sections_to_use)}")
    
    # Distribute questions across sections (ensure each section gets at least 1 if possible)
    num_questions = args.num_questions
    num_sections = len(sections_to_use)
    
    if num_questions < num_sections:
        # If fewer questions than sections, use first N sections
        sections_to_use = sections_to_use[:num_questions]
        num_sections = len(sections_to_use)
        print(f"Note: Only {num_questions} questions requested, using {num_sections} sections")
    
    # Distribute evenly, ensuring each section gets at least 1
    questions_per_section = max(1, num_questions // num_sections)
    remainder = num_questions % num_sections
    
    section_assignments = []
    # First pass: give each section at least 1 question
    for section in sections_to_use:
        section_assignments.append(section)
    
    # Second pass: distribute remaining questions
    for i in range(num_questions - num_sections):
        section_assignments.append(sections_to_use[i % num_sections])
    
    # Shuffle to avoid predictable patterns
    import random
    random.shuffle(section_assignments)
    
    print(f"\nQuestion distribution:")
    from collections import Counter
    for section, count in Counter(section_assignments).items():
        print(f"  - {section}: {count} question(s)")
    
    # Retrieve style examples - ensure diversity
    style_examples = None
    if retriever:
        print(f"\nRetrieving {args.style_examples} style examples...")
        style_examples = retriever.retrieve_style_examples(
            section=None,
            n_examples=args.style_examples,
            difficulty=args.difficulty,
            ensure_diversity=True
        )
        print(f"✓ Retrieved {len(style_examples)} examples")
    
    # Generate and evaluate questions individually
    print(f"\n{'='*60}")
    print(f"Generating {args.num_questions} individual questions")
    print(f"{'='*60}\n")
    
    all_approved_questions = []
    total_generated = 0
    total_approved = 0
    
    for i, section in enumerate(section_assignments, 1):
        print(f"\n[{i}/{args.num_questions}] Generating question for '{section}' section...")
        
        # Get diverse examples - use semantic search for better diversity
        section_examples = None
        if retriever:
            # Use semantic search to find diverse questions in this section
            # Query based on section but encourage diversity
            query = f"{section} programming question {args.difficulty} difficulty"
            section_examples = retriever.retrieve_by_query(
                query=query,
                n_results=8,  # Get more to have variety
                section_filter=None  # Don't filter by section - use semantic similarity
            )
            
            # Normalize section names for matching
            def normalize_section(s):
                if not s:
                    return ""
                s = s.strip()
                if "1D Array" in s or "1-D Array" in s:
                    return "1D Arrays"
                if "2D Array" in s or "2-D Array" in s:
                    return "2D Arrays"
                if "Function" in s and "Array" in s:
                    return "Functions and Arrays"
                return s
            
            normalized_section = normalize_section(section)
            
            # Keep questions from same or related sections
            filtered_examples = []
            for ex in section_examples:
                ex_section = normalize_section(ex.get('section', ''))
                if ex_section == normalized_section:
                    filtered_examples.append(ex)
            
            # If we have enough from exact section, use those; otherwise use broader results
            if len(filtered_examples) >= 3:
                section_examples = filtered_examples[:4]
            else:
                # Use broader results for diversity
                section_examples = section_examples[:4]
        
        # Fallback to provided style examples if retriever didn't work
        if not section_examples and style_examples:
            # Use diverse examples from style_examples
            section_examples = [ex for ex in style_examples if ex.get('section') == section]
            if len(section_examples) < 3:
                # Add some from other sections for diversity
                other_examples = [ex for ex in style_examples if ex.get('section') != section]
                section_examples.extend(other_examples[:2])
            section_examples = section_examples[:4]  # Limit to 4 examples
        
        # Generate individual question (marks inferred from reference questions)
        question = generator.generate_question(
            section=section,
            style_examples=section_examples,
            difficulty=args.difficulty
        )
        
        if not question:
            print(f"  ✗ Failed to generate question")
            continue
        
        total_generated += 1
        print(f"  ✓ Generated question")
        
        # Evaluate individual question
        print(f"  Evaluating question...")
        evaluation = critic.evaluate_question(question, section_examples)
        score = evaluation.get('score', 0)
        approved = evaluation.get('approved', False)
        
        print(f"  Quality score: {score:.1f}/10, Approved: {approved}")
        
        # Save if meets minimum score
        if score >= args.min_score:
            try:
                # Convert question to dict
                question_dict = question.model_dump() if hasattr(question, 'model_dump') else question
                question_dict['difficulty'] = args.difficulty
                question_dict['quality_score'] = score
                question_dict['generated_date'] = datetime.now().strftime("%Y-%m-%d")
                
                # Remove exam-specific fields
                if 'question_number' in question_dict:
                    del question_dict['question_number']
                if 'marks' in question_dict:
                    del question_dict['marks']
                if 'explanation' in question_dict and not question_dict.get('explanation'):
                    del question_dict['explanation']
                
                all_approved_questions.append(question_dict)
                total_approved += 1
                print(f"  ✓ Question approved and added to bank")
            except Exception as e:
                print(f"  ✗ Error processing question: {e}")
        else:
            print(f"  ✗ Question rejected (score {score:.1f} < {args.min_score})")
    
    print(f"\n{'='*60}")
    print(f"Generation complete!")
    print(f"  Generated: {total_generated} questions")
    print(f"  Approved: {total_approved} questions (score >= {args.min_score})")
    print(f"{'='*60}")
    
    # Save approved questions to question bank
    if all_approved_questions:
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
            print(f"\nSaving to: {output_path.absolute()}")
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(all_questions, f, indent=2, ensure_ascii=False)
            
            # Verify file was written
            if output_path.exists() and output_path.stat().st_size > 0:
                print(f"✓ File saved successfully ({output_path.stat().st_size} bytes)")
            else:
                print(f"✗ Warning: File may be empty or not saved correctly")
            
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
            if all_approved_questions:
                print(f"\n  New questions by section:")
                for section, count in sections_used.items():
                    print(f"    - {section}: {count} question(s)")
                print(f"\n  New questions by difficulty:")
                for diff, count in difficulties_used.items():
                    print(f"    - {diff}: {count} question(s)")
            else:
                print(f"\n  ⚠ No approved questions to add (all scores < {args.min_score})")
            print(f"{'='*60}")
            
            # Optionally add new questions to vector database
            if all_approved_questions:
                print(f"\nWould you like to add these questions to the vector database?")
                print(f"This allows them to be used as style examples in future generations.")
                print(f"Run: py src/add_to_vector_db.py --file {output_path.name}")
        except Exception as e:
            print(f"\n✗ Error saving question bank: {e}")
            import traceback
            traceback.print_exc()
            return 1
    else:
        print("\n✗ No approved questions to save")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())

