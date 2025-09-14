# 🧮 JEE Mains Maths Solver  

An **AI-powered web application** that solves **JEE Mains mathematics problems** step-by-step using **AI**.  
Built with **Flask**, it supports both **text input** and **image upload**, making it a flexible study assistant for students preparing for competitive exams.  

---

## 🚀 Features

- 📘 **Step-by-step math solutions** for JEE Mains-level problems.
- ✍️ **Text-based input**: Type your math question directly.
- 🖼️ **Image-based input**: Upload a math question image (PNG/JPG/JPEG).
- 🔎 **AI-powered extraction** of math questions from images.
- ✅ **Structured JSON validation** with **Pydantic** to ensure clean, predictable outputs.
- 🎨 **Responsive frontend** built with **Bootstrap 5**.
- 🔗 **REST API** (`/api/solve`) to programmatically solve math problems.
- 💡 **Sample problems** on the homepage for quick demos.
- ⚡ Deployable on **Render (PaaS)**, with support for **Docker**, **Heroku**, and **Vercel**.

---

## 🧠 Technical Breakdown

### 1. **Prompt Engineering**
The app carefully designs prompts for Gemini to ensure:
- Solutions are **step-by-step** with clear reasoning.
- JSON output is strictly validated to prevent parsing errors.
- Metadata such as **topic** (Algebra, Calculus, etc.) and **difficulty level** (Easy/Medium/Hard) is included.

👉 Example prompt components:
- Restates the question clearly.
- Explains reasoning in **chronological order**.
- Outputs a **strict JSON block** only.

---

### 2. **Data Pipelining**
- **Input Handling**:
  - Text input → directly processed.
  - Image input → passed through **Gemini multimodal** to extract the math question.
- **Validation**:
  - JSON responses from Gemini are parsed and validated with **Pydantic** (`MathSolution` model).
- **Transformation**:
  - Escapes problematic characters (like backslashes) to prevent `JSONDecodeError`.
- **Presentation**:
  - Markdown + Highlight.js + KaTeX for rendering math notation and code formatting.

---

### 3. **Application Structure**

#### 🔹 Backend (Flask)
- `app.py`:
  - Routes:
    - `/` → Input form.
    - `/solve` → Solves problem from form (text/image).
    - `/api/solve` → JSON API.
    - `/health` → Health check.
  - Error handlers (404, 500).
  - Logging for debugging and error tracing.
  - Image processing with **Pillow**.

#### 🔹 Frontend (Jinja + Bootstrap)
- **Templates**:
  - `base.html` → Global layout, navbar, flash messages, Bootstrap, KaTeX, Highlight.js.
  - `index.html` → Question input form + sample problems.
  - `solution.html` → Displays step-by-step solution, summary, difficulty, topic, and raw AI JSON.
  - `error.html` → User-friendly error page.

---

### 4. **Deployment Options**
- **Render** → Primary hosting (PaaS).
- **Dockerfile** → Containerized deployment.
- **Procfile** → Heroku support (runs Gunicorn).
- **vercel.json** → Serverless deployment option via Vercel.

---

### 5. **Dependencies**
From `requirements.txt`:
- `Flask` → Web framework.
- `google-generativeai` → Gemini API.
- `python-dotenv` → Environment variable management.
- `pydantic` → JSON validation.
- `markdown` → Render markdown text.
- `Pillow` → Image processing.
- `gunicorn` → Production WSGI server.

---

## ⚙️ Setup & Installation

### 1. Clone Repository
```bash
git clone https://github.com/your-username/jee-mains-maths-solver.git
cd jee-mains-maths-solver
