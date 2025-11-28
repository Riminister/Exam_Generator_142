# How to Specify Sections for Question Generation

## Method 1: Command Line Argument (Recommended)

Use the `--sections` argument to specify which sections you want:

```bash
# Generate questions from specific sections
py main.py --sections "1D Arrays" "Functions" "Algorithms"

# Generate questions from multiple sections
py main.py --sections "Program Comprehension" "Computation and Output" "2D Arrays"

# With other options
py main.py --marks 100 --difficulty medium --sections "1D Arrays" "Functions" --iterations 1
```

**Important:** Section names must match exactly (case-sensitive). Use quotes if section names contain spaces.

## Method 2: View Available Sections

To see all available sections in your question bank:

```bash
cd exam-generator
py -c "import json; data = json.load(open('data/question_bank.json', encoding='utf-8')); sections = sorted(set(q['section'] for exam in data for q in exam['questions'])); print('Available sections:'); [print(f'  - {s}') for s in sections]"
```

Or check the sections programmatically:
```python
from src.retriever import QuestionRetriever
r = QuestionRetriever()
stats = r.get_section_statistics()
for section, count in sorted(stats.items(), key=lambda x: x[1], reverse=True):
    print(f"{section}: {count} questions")
```

## Method 3: Modify Default Sections in Code

If you want to change the default sections (when `--sections` is not provided), edit `exam-generator/src/generator.py`:

```python
# Around line 232-242
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
```

## Common Section Names

Based on your question bank, common sections include:
- Program Comprehension
- Computation and Output
- Computation and Numerical Methods
- 1D Arrays (or "1-D Arrays")
- 2D Arrays (or "2-D Arrays")
- Functions
- Algorithms
- Algorithms: Sorting and Searching
- Robot Programming (or "Robot Operation", "NXT Robot Operation")
- Design Thinking
- Simulating a Physical Problem
- Function and 1D Arrays
- Functions and 1-D Arrays
- 2D Array and Function

## Examples

```bash
# Generate only array-related questions
py main.py --sections "1D Arrays" "2D Arrays" --difficulty medium

# Generate only function questions
py main.py --sections "Functions" --difficulty hard

# Generate mixed topics
py main.py --sections "Program Comprehension" "Algorithms" "Computation and Output" --marks 100

# Let it auto-select (uses top 8 sections from database)
py main.py --marks 100 --difficulty medium
```

## Notes

- If you don't specify `--sections`, the system will automatically select the top 8 most common sections from your question bank
- Section names are case-sensitive and must match exactly
- Use quotes around section names that contain spaces
- Multiple sections can be specified - questions will be distributed evenly across them

