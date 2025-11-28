# Exam Generator for APSC 142

## Overview
This project aims to create a program that generates PDF or Word documents containing full-length practice exams for students taking APSC 142 (Introduction to Coding) at Queen's University.

## Goal
Successfully create a program that can generate PDF or Word type documents that create a full practice exam for students for APSC 142 introduction to coding.

## Project Steps

1. **Download all past exams from Queen's exam bank**
   - Collect historical exam materials for APSC 142

2. **Set up OpenAI API Key**
   - Configure API access for OpenAI services

3. **Parse exam questions using OpenAI API** ✅
   - Use OpenAI API to parse through every question in the exams and extract them
   - Extract images and convert them to text descriptions
   - Extract equations and convert them to readable text
   - Output structured JSON format

4. **Create JSON database of questions** ✅
   - Store all old exam questions in a structured JSON file
   - See `parse_pdf_exams.py` for the parser implementation

5. **Generate vector embeddings**
   - Use OpenAI API vector embedding to embed all the questions for semantic search

6. **Create ML model for exam generation**
   - Pair a machine learning model with OpenAI API key to create full-length exams

7. **Present to Sean Kauffman**
   - Final presentation and deployment

## Setup

1. Install required dependencies:
   ```bash
   py -m pip install -r requirements.txt
   ```
   
   **Optional - For OCR support:**
   - Install Tesseract OCR: https://github.com/UB-Mannheim/tesseract/wiki
   - Add Tesseract to your system PATH

2. Create a `.env` file in the root directory with your OpenAI API key:
   ```
   OPENAI_API_KEY=your_api_key_here
   ```

3. Test your API key:
   ```bash
   py test_api_key.py
   ```

4. Parse PDF exams:
   ```bash
   py parse_pdf_exams.py
   ```
   See `USAGE.md` for detailed usage instructions.

## Project Structure
```
Exam_Generator_142/
├── README.md
├── USAGE.md
├── Game_Plan.txt
├── requirements.txt
├── parse_pdf_exams.py
├── .env
├── Past_Exams/          # PDF exam files
└── Questions/           # Generated JSON files
```

## Notes
- Make sure to keep your `.env` file secure and never commit it to version control
- Add `.env` to your `.gitignore` file

