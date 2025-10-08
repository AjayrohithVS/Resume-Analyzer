import os
import re
from flask import Flask, request, render_template
from werkzeug.utils import secure_filename
from pdfminer.high_level import extract_text
from docx import Document
import google.generativeai as genai
from dotenv import load_dotenv
import json

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'docx'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ---------------- Setup Google Generative AI ---------------- #
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

model = genai.GenerativeModel("gemini-1.5-flash")

# ---------------- Helpers ---------------- #
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_pdf(file_path):
    return extract_text(file_path)

def extract_text_from_docx(file_path):
    doc = Document(file_path)
    return '\n'.join([para.text for para in doc.paragraphs])

def extract_resume_text(file_path):
    if file_path.endswith('.pdf'):
        return extract_text_from_pdf(file_path)
    elif file_path.endswith('.docx'):
        return extract_text_from_docx(file_path)
    else:
        return ""

# ---------------- AI Analysis ---------------- #
def analyze_resume_with_ai(resume_text, job_description):
    prompt = f"""
    You are an AI Resume Analyzer for a job portal.
    Compare the following resume with the job description.

    --- Resume ---
    {resume_text}

    --- Job Description ---
    {job_description}

    Respond ONLY in valid JSON with the following keys:
    {{
        "score": <int from 0 to 100>,
        "matched_skills": [list of matched skills],
        "missing_skills": [list of missing skills],
        "recommendation": "short summary recommendation"
    }}
    """

    response = model.generate_content(prompt)
    raw_text = response.text.strip()

    # 🟢 Debug: print what Gemini actually returned
    print("=== Gemini Raw Response ===")
    print(raw_text)
    print("===========================")

    # 🟢 Clean Gemini's Markdown formatting if present
    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")
        raw_text = raw_text.replace("json", "", 1).strip()

    try:
        data = json.loads(raw_text)
        return data
    except Exception:
        # Fallback: show raw text in recommendation
        return {
            "score": None,
            "matched_skills": [],
            "missing_skills": [],
            "recommendation": raw_text
        }


# ---------------- Routes ---------------- #
@app.route('/', methods=['GET', 'POST'])
def index():
    result = None
    if request.method == 'POST':
        job_description = request.form['job_description']
        file = request.files['resume']

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            resume_text = extract_resume_text(filepath)
            result = analyze_resume_with_ai(resume_text, job_description)

    return render_template('index.html', result=result)

if __name__ == '__main__':
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run(debug=True)
