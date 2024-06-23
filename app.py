import io
import os
import json
import uuid
from flask import Flask, request, render_template_string, redirect, url_for, send_file, session, flash
import google.generativeai as genai
from PyPDF2 import PdfReader
from reportlab.lib.pagesizes import letter
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import black
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Create a directory for storing user data
if not os.path.exists('user_data'):
    os.makedirs('user_data')

def save_user_data(user_id, data):
    with open(f'user_data/{user_id}.json', 'w') as f:
        json.dump(data, f)

def load_user_data(user_id):
    try:
        with open(f'user_data/{user_id}.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {'pdf_content': None, 'qa_history': [], 'chat_history': [], 'api_key': None}

# ... [keep the extract_text_from_pdf and create_qa_pdf functions as they are] ...
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

@app.route('/', methods=['GET', 'POST'])
def index():
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
    
    user_data = load_user_data(session['user_id'])
    
    if request.method == 'POST':
        if 'api_key' in request.form:
            api_key = request.form['api_key']
            user_data['api_key'] = api_key
            save_user_data(session['user_id'], user_data)
            flash('API Key saved successfully!', 'success')
            return redirect(url_for('index'))
        
        if not user_data['api_key']:
            flash('Please enter your Google API Key first!', 'error')
            return redirect(url_for('index'))
        
        genai.configure(api_key=user_data['api_key'])
        
        if 'file' in request.files:
            file = request.files['file']
            if file and file.filename.endswith('.pdf'):
                user_data['pdf_content'] = extract_text_from_pdf(file)
                
                user_data['chat_history'] = [
                    {
                        "role": "user",
                        "parts": ["I want you to act as a 10 mark answer generator bot. I will provide you with the content of a PDF, and I need you to read and understand it. Then I will ask questions, and for every question, I need you to give a 10 mark answer from the information in the PDF and your own knowledge combined. Here's the PDF content:\n\n" + user_data['pdf_content']],
                    },
                    {
                        "role": "model",
                        "parts": ["Understood. I have processed the PDF content you provided. I'm ready to answer your questions based on this information combined with my existing knowledge. Please go ahead and ask your questions."],
                    },
                ]
                save_user_data(session['user_id'], user_data)
                flash('PDF uploaded successfully!', 'success')
                return redirect(url_for('index'))
        
        elif 'question' in request.form:
            question = request.form['question']
            if user_data['pdf_content']:
                try:
                    model = genai.GenerativeModel(model_name="gemini-1.5-pro")
                    chat = model.start_chat(history=user_data['chat_history'])
                    response = chat.send_message(question)
                    user_data['chat_history'].append({"role": "user", "parts": [question]})
                    user_data['chat_history'].append({"role": "model", "parts": [response.text]})
                    user_data['qa_history'].append((question, response.text))
                    save_user_data(session['user_id'], user_data)
                except Exception as e:
                    flash(f'Error: {str(e)}. Please check your API key.', 'error')
                return redirect(url_for('index'))
            else:
                flash('Please upload a PDF first!', 'error')
                return redirect(url_for('index'))
        
        elif 'clear_history' in request.form:
            user_data['qa_history'] = []
            user_data['chat_history'] = []
            save_user_data(session['user_id'], user_data)
            flash('History cleared successfully!', 'success')
            return redirect(url_for('index'))
    
    return render_template_string(HTML_TEMPLATE, qa_history=user_data['qa_history'], file_uploaded=bool(user_data['pdf_content']), api_key_set=bool(user_data['api_key']))

@app.route('/download_pdf')
def download_pdf():
    user_data = load_user_data(session['user_id'])
    pdf_buffer = create_qa_pdf(user_data['qa_history'])
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
        textarea, input[type="file"], input[type="submit"], input[type="text"] { margin-bottom: 10px; }
        textarea { width: 100%; height: 100px; }
        .qa-pair { background-color: #f4f4f4; padding: 15px; margin-bottom: 15px; border-radius: 5px; }
        .question { font-weight: bold; }
        .answer { white-space: pre-wrap; }
        .download-btn { display: inline-block; padding: 10px 20px; background-color: #4CAF50; color: white; text-decoration: none; border-radius: 5px; }
        .clear-btn { display: inline-block; padding: 10px 20px; background-color: #f44336; color: white; text-decoration: none; border-radius: 5px; }
        .flash { padding: 10px; margin-bottom: 10px; border-radius: 5px; }
        .flash.error { background-color: #ffcccc; border: 1px solid #ff0000; }
        .flash.success { background-color: #ccffcc; border: 1px solid #00ff00; }
    </style>
</head>
<body>
    <h1>PDF Question Answering</h1>
    
    {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            {% for category, message in messages %}
                <div class="flash {{ category }}">{{ message }}</div>
            {% endfor %}
        {% endif %}
    {% endwith %}
    
    {% if not api_key_set %}
    <h2>Set Your Google API Key</h2>
    <form method="post">
        <input type="text" name="api_key" placeholder="Enter your Google API Key" required>
        <input type="submit" value="Save API Key">
    </form>
    {% endif %}
    
    {% if api_key_set %}
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
        <form method="post" style="display: inline;">
            <input type="hidden" name="clear_history" value="true">
            <input type="submit" value="Clear Q&A History" class="clear-btn">
        </form>
    {% endif %}
    {% for question, answer in qa_history %}
        <div class="qa-pair">
            <div class="question">Q: {{ question }}</div>
            <div class="answer">A: {{ answer }}</div>
        </div>
    {% endfor %}
    {% endif %}
</body>
</html>
'''

if __name__ == '__main__':
     app.run(host='0.0.0.0',port=5000)
