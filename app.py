import os
import io
from flask import Flask, request, render_template_string, redirect, url_for, send_file
import google.generativeai as genai
from PyPDF2 import PdfReader
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.colors import black, grey
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.colors import black
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

app = Flask(__name__)

# Configure Gemini API
genai.configure(api_key="AIzaSyBtn0zbLIA1vp6AGgHXY_OyW88-CIal-2o")

def extract_text_from_pdf(file):
    """Extracts text content from a PDF file."""
    pdf_reader = PdfReader(file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text() + "\n"
    return text

def create_qa_pdf(qa_history):
    """Creates a well-formatted PDF from the Q&A history."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
    styles = getSampleStyleSheet()
    
    # Custom styles
    styles.add(ParagraphStyle(name='Justify', alignment=TA_JUSTIFY))
    styles.add(ParagraphStyle(name='Question', 
                              parent=styles['Heading2'], 
                              fontSize=12, 
                              spaceAfter=6,
                              textColor=black,
                              bold=True))
    styles.add(ParagraphStyle(name='Answer', 
                              parent=styles['Normal'], 
                              fontSize=12, 
                              spaceAfter=12,
                              textColor=black,
                              leading=14))

    story = []

    for i, (question, answer) in enumerate(qa_history, 1):
        # Clean up the text
        question = question.replace('*', '').replace('\n', ' ').strip()
        answer = answer.replace('*', '').strip()
        
        # Add question
        story.append(Paragraph(f"Q{i}: {question}", styles['Question']))
        
        # Add answer paragraphs
        paragraphs = answer.split('\n')
        for para in paragraphs:
            # Check if paragraph is a numbered point
            if para.strip().startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.')):
                story.append(Paragraph(para.strip(), styles['Answer']))
            else:
                story.append(Paragraph(para, styles['Answer']))
        
        story.append(Spacer(1, 24))

    doc.build(story)
    buffer.seek(0)
    return buffer

# Create the model
generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 8192,
}

model = genai.GenerativeModel(
    model_name="gemini-1.5-pro",
    generation_config=generation_config,
)

chat_session = None
pdf_content = None
qa_history = []

@app.route('/', methods=['GET', 'POST'])
def index():
    global chat_session, pdf_content, qa_history
    
    if request.method == 'POST':
        if 'file' in request.files:
            file = request.files['file']
            if file and file.filename.endswith('.pdf'):
                pdf_content = extract_text_from_pdf(file)
                
                chat_session = model.start_chat(
                    history=[
                        {
                            "role": "user",
                            "parts": ["I want you to act as a 10 mark answer generator bot. I will provide you with the content of a PDF, and I need you to read and understand it. Then I will ask questions, and for every question, I need you to give a 10 mark answer from the information in the PDF and your own knowledge combined. Here's the PDF content:\n\n" + pdf_content],
                        },
                        {
                            "role": "model",
                            "parts": ["Understood. I have processed the PDF content you provided. I'm ready to answer your questions based on this information combined with my existing knowledge. Please go ahead and ask your questions."],
                        },
                    ]
                )
                return redirect(url_for('index'))
        
        elif 'question' in request.form:
            question = request.form['question']
            if chat_session and pdf_content:
                response = chat_session.send_message(question)
                qa_history.append((question, response.text))
                return redirect(url_for('index'))
    
    return render_template_string(HTML_TEMPLATE, qa_history=qa_history, file_uploaded=bool(pdf_content))

@app.route('/download_pdf')
def download_pdf():
    pdf_buffer = create_qa_pdf(qa_history)
    return send_file(pdf_buffer, as_attachment=True, download_name="qa_history.pdf", mimetype="application/pdf")

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>PDF Q&A</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; padding: 20px; }
        h1, h2 { color: #333; }
        form { margin-bottom: 20px; }
        textarea, input[type="file"], input[type="submit"] { margin-bottom: 10px; }
        textarea { width: 100%; height: 100px; }
        .qa-pair { background-color: #f4f4f4; padding: 15px; margin-bottom: 15px; border-radius: 5px; }
        .question { font-weight: bold; }
        .answer { white-space: pre-wrap; }
        .download-btn { display: inline-block; padding: 10px 20px; background-color: #4CAF50; color: white; text-decoration: none; border-radius: 5px; }
    </style>
</head>
<body>
    <h1>PDF Question Answering</h1>
    
    <h2>Upload a PDF</h2>
    <form method="post" enctype="multipart/form-data">
        <input type="file" name="file" accept=".pdf">
        <input type="submit" value="Upload">
    </form>

    <h2>Ask a Question</h2>
    <form method="post">
        <textarea name="question" placeholder="Enter your question" required></textarea><br>
        <input type="submit" value="Ask">
    </form>
    
    <h2>Q&A History</h2>
    {% if qa_history %}
        <a href="{{ url_for('download_pdf') }}" class="download-btn">Download Q&A History as PDF</a>
    {% endif %}
    {% for question, answer in qa_history %}
        <div class="qa-pair">
            <div class="question">Q: {{ question }}</div>
            <div class="answer">A: {{ answer }}</div>
        </div>
    {% endfor %}
</body>
</html>
'''

if __name__ == '__main__':
    app.run(debug=True)