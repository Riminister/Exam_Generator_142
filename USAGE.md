# PDF Exam Parser Usage Guide

## Overview
The `parse_pdf_exams.py` script extracts questions from PDF exam files, handles images and equations, and outputs structured JSON.

## Features
- ✅ Text extraction from PDFs
- ✅ Image extraction and description using GPT-4 Vision
- ✅ Equation detection and conversion to text
- ✅ OCR support for scanned PDFs
- ✅ JSON output with structured question data

## Installation

1. Install Python dependencies:
```bash
py -m pip install -r requirements.txt
```

2. **Optional - For OCR support:**
   - Install Tesseract OCR: https://github.com/UB-Mannheim/tesseract/wiki
   - Add Tesseract to your system PATH
   - The script will automatically use OCR if available

## Usage

### Basic Usage (Process all PDFs)
```bash
py parse_pdf_exams.py
```

This will:
- Find all PDF files in `Exam_Generator_142/Past_Exams/` or `Past_Exams/`
- Extract questions from each PDF
- Save individual JSON files to `Questions/` directory
- Create a combined `all_questions.json` file

### Process a Specific PDF
```bash
py parse_pdf_exams.py --file APSC142APR.pdf
```

### Use OCR for Scanned PDFs
```bash
py parse_pdf_exams.py --ocr
```

## Output Format

The script generates JSON files with the following structure:

```json
{
  "source_file": "APSC142APR.pdf",
  "total_questions": 10,
  "questions": [
    {
      "question_number": 1,
      "question_text": "What is the output of the following code?",
      "answer_choices": ["A) 5", "B) 10", "C) 15"],
      "source_page": 1,
      "source_file": "APSC142APR.pdf",
      "images": [
        {
          "description": "A flowchart showing the program execution...",
          "position": {"x0": 100, "y0": 200, "x1": 400, "y1": 500},
          "format": "png"
        }
      ],
      "equations": [
        {
          "original": "f(x) = x^2 + 2x + 1",
          "text_description": "The function f of x equals x squared plus 2x plus 1"
        }
      ]
    }
  ]
}
```

## How It Works

1. **Text Extraction**: Uses `pdfplumber` for better text extraction, falls back to PyMuPDF
2. **Image Processing**: 
   - Extracts images from PDF pages
   - Uses GPT-4 Vision API to describe images in text
   - Associates images with questions on the same page
3. **Equation Handling**:
   - Detects equations using pattern matching
   - Uses GPT to convert equations to readable text descriptions
4. **Question Parsing**:
   - Uses GPT-4o to intelligently parse questions from text
   - Extracts question numbers, text, and answer choices
   - Falls back to simple pattern matching if GPT parsing fails

## Troubleshooting

### "Connection error" when describing images
- Check your OpenAI API key in `.env`
- Ensure you have credits in your OpenAI account
- GPT-4 Vision API requires a paid account

### OCR not working
- Install Tesseract OCR
- Add Tesseract to system PATH
- Install `pytesseract` and `pdf2image` packages

### No questions extracted
- Check if the PDF has selectable text (not just images)
- Try using `--ocr` flag for scanned PDFs
- Check the console output for warnings

### High API costs
- The script makes multiple API calls per page (images, equations, question parsing)
- Consider processing one PDF at a time with `--file` flag
- Monitor your OpenAI usage dashboard

## Next Steps

After parsing, you can:
1. Review the JSON files in the `Questions/` directory
2. Use the questions for Step 4: Create vector embeddings
3. Build your exam generator using the structured question data

