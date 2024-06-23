
```markdown
# PDF Question Answering Web Application

This web application allows users to upload PDF documents, ask questions about the content, and receive AI-generated answers. It uses Google's Gemini AI for natural language processing and question answering.

## Features

- PDF upload and text extraction
- AI-powered question answering based on PDF content
- Persistent Q&A history display
- Option to download Q&A history as a formatted PDF

## Requirements

- Python 3.7+
- Flask
- google-generativeai
- PyPDF2
- reportlab

## Setup

1. Clone this repository:
   ```
   git clone https://github.com/kumar-017/PDF_QNA.git <br>
   cd PDF_QNA
   ```

2. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

3. Set up your Gemini API key:
   - Obtain an API key from the Google AI Studio
   - Set it as an environment variable:
     ```
     export GEMINI_API_KEY=your_api_key_here
     ```

4. Run the application:
   ```
   python app.py
   ```

5. Open a web browser and navigate to `http://localhost:5000`

## Usage

1. Upload a PDF file using the provided form.
2. Enter questions about the PDF content in the text area.
3. View AI-generated answers displayed on the page.
4. (Optional) Download the Q&A history as a formatted PDF.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
```
