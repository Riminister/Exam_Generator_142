# Exam Generator

Automated exam generation system for APSC 142 using vector embeddings and LLM.

## Architecture

```
Raw JSON Data → Parse & Embed → Vector Database
Vector Database → Retrieve Style Examples → Generation Engine
Generation Engine → Draft Questions → Feedback Loop → Final Exam
```

## Directory Structure

```
exam-generator/
├── data/
│   └── question_bank.json       # Source question data
├── src/
│   ├── models.py                # Pydantic schemas
│   ├── ingest.py                # Load JSON → Vector DB
│   ├── retriever.py             # Fetch style examples
│   ├── generator.py             # LLM exam generation
│   └── critic.py                # Question evaluation
├── output/
│   └── new_exam_v1.json         # Generated exams
├── chroma_db/                    # Vector database (created automatically)
├── .env                          # API keys
└── main.py                       # Entry point
```

## Setup

1. Install dependencies:
```bash
py -m pip install -r ../requirements.txt
```

2. Ensure `.env` file exists with your OpenAI API key:
```
OPENAI_API_KEY=your_key_here
```

## Usage

### Step 1: Ingest Question Bank
Load questions into vector database:
```bash
cd exam-generator
py src/ingest.py
```

This will:
- Load `data/question_bank.json`
- Create embeddings for all questions
- Store in ChromaDB with relevance scores (difficulty + date)

### Step 2: Generate Exam
Generate a new exam:
```bash
py main.py --marks 100 --difficulty medium
```

Options:
- `--marks`: Target total marks (default: 100)
- `--difficulty`: easy, medium, or hard (default: medium)
- `--num-questions`: Number of questions (auto-calculated if not specified)
- `--sections`: Specific sections to include
- `--style-examples`: Number of style examples to retrieve (default: 5)
- `--iterations`: Feedback loop iterations (default: 2)
- `--output`: Output file path (default: output/new_exam_v1.json)

### Example
```bash
# Generate medium difficulty exam with 100 marks
py main.py --marks 100 --difficulty medium --iterations 3

# Generate hard exam with specific sections
py main.py --marks 120 --difficulty hard --sections "Arrays" "Functions"
```

## How It Works

1. **Ingest (A)**: Questions are embedded with relevance scoring based on:
   - Difficulty (marks relative to exam total)
   - Date relevance (newer exams weighted higher)

2. **Retrieve (B)**: Style examples are retrieved from vector DB using semantic search

3. **Generate (C)**: LLM generates questions matching style and difficulty

4. **Critic (D)**: Generated questions are evaluated for quality

5. **Feedback Loop**: Process repeats with refinements until exam is approved

## Output

Generated exams are saved as JSON in `output/` directory with structure:
```json
{
  "exam_metadata": {
    "university": "Queen's University",
    "course": "APSC 142",
    "date": "Generated"
  },
  "questions": [
    {
      "question_number": "1",
      "section": "Arrays",
      "marks": 15,
      "text": "..."
    }
  ]
}
```

