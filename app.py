from flask import Flask, render_template, request, redirect, session, flash, jsonify, url_for
import google.generativeai as genai
from dotenv import load_dotenv
import os
from pydantic import BaseModel, Field, ValidationError
from typing import List, Optional
import markdown
import logging
from datetime import datetime
import json
from json import JSONDecodeError
from PIL import Image
from io import BytesIO
from werkzeug.utils import secure_filename


load_dotenv()  # Load environment variables from .env

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-here')

# Configure Gemini API
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

class MathSolution(BaseModel):
    """Pydantic model for validating math solution response"""
    question: str = Field(..., description="The original math question")
    solution_steps: List[str] = Field(..., description="Step-by-step solution")
    final_answer: str = Field(..., description="The final answer")
    difficulty_level: Optional[str] = Field(None, description="Difficulty level (Easy/Medium/Hard)")
    topic: Optional[str] = Field(None, description="Math topic (e.g., Calculus, Algebra, etc.)")

class JEEMathSolver:
    def __init__(self):
        self.model = genai.GenerativeModel('gemini-2.0-flash')
        
    def create_prompt(self, question: str) -> str:
        """Create a structured prompt for JEE Mains math problems"""
        prompt = f"""
Behave like you are a top level JEE Mains mathematics tutor. Solve the following math problem step by step.
Think deeply and process the request for the answer of the question in a chronological order

### Question: {question}

### Understanding and explaining the answer to the question :
- Show all mathematical working clearly
- Use proper mathematical notation
- Explain the reasoning behind each step
- Highlight any important formulas or theorems used

### Task :
1. Return ONLY valid JSON - no trailing commas, code or text in the output
2. No text before or after the JSON object and the JSON object should be a single, valid block
3. All strings must be properly escaped
4. Do not invent or assume facts
5. If unconfirmed, say : "I do not have that information"

### Answer Format
**Question:** [Restate the question and it's understanding clearly]        
**Solution Steps:**
1. [First step with clear explanation]
2. [Second step with clear explanation]
3. [Continue with all necessary steps]     
**Final Answer:** [Provide the final numerical answer or expression]
**Difficulty Level:** [Easy/Medium/Hard based on JEE Mains Maths standards]
**Topic:** [Identify the mathematical concept out of given topics - Algebra, Calculus, Coordinate Geometry, Statistics, Trigonometry]

### Required JSON Structure:
    {{
    "question": "Find the derivative of f(x) = x³ + 2x² - 5x + 1"
    solution_steps: ["Step 1: Apply the Sum/Difference Rule 
    The derivative of a sum or difference of terms is the sum or difference of their individual derivatives.", 
    "Step 2: Apply the Power Rule and Constant Multiple Rule
    We will now differentiate each term separately.", 
    "Step 3: Combine the Results
    Now, we combine the derivatives of all the individual terms to get the final answer."]
    final_answer: "The derivative of the function f(x)=x³ + 2x² - 5x + 1 is f′(x)=3x² + 4x - 5"
    difficulty_level: "Easy"
    topic: "Calculus"
    }}        
"""
        return prompt
    
    def solve_problem(self, question: str) -> dict:
        """Sends the question to the AI and returns the parsed solution or an error."""
        try:
            response = self.model.generate_content(
                self.create_prompt(question),
                generation_config=genai.types.GenerationConfig(
                    response_mime_type="application/json"
                ),
            )
            raw_response_text = response.text
            
            # Find the JSON object within the response text
            json_start = raw_response_text.find('{')
            json_end = raw_response_text.rfind('}') + 1
            json_text = raw_response_text[json_start:json_end]
            
            # FIX: Escape backslashes to prevent JSONDecodeError
            escaped_json_text = json_text.replace('\\', '\\\\')
            
            # Now, safely parse the JSON string
            json_data = json.loads(escaped_json_text)

            # Validate the parsed data with pydantic
            solution = MathSolution(**json_data)
            
            return {
                "success": True,
                "solution": solution,
                "raw_response": markdown.markdown(raw_response_text)
            }
            
        except JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            return {
                "success": False,
                "error": f"Failed to parse AI response as JSON: {e}"
            }
        except ValidationError as e:
            logger.error(f"Failed to validate AI response: {e}")
            return {
                "success": False,
                "error": f"Failed to validate AI response: {e}"
            }
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            return {
                "success": False,
                "error": f"An unexpected error occurred: {e}"
            }
        
def solve_problem_from_image(image_file):
    """
    Extracts text from an image and returns the content.
    """
    try:
        # Check for allowed image extensions
        ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
        def allowed_file(filename):
            return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

        if not allowed_file(image_file.filename):
            return {"success": False, "error": "Invalid file type. Only PNG, JPG, and JPEG are allowed."}

        # Read the image file and open it with PIL
        img_bytes = image_file.read()
        image = Image.open(BytesIO(img_bytes))

        # Create the multimodal prompt
        prompt = [
            "What is the math question in this image? Please provide only the extracted text of the question, without any additional explanations or formatting.",
            image
        ]
        
        # Generate content from the model
        response = genai.GenerativeModel('gemini-1.5-flash').generate_content(prompt)
        extracted_text = response.text.strip()
        
        if not extracted_text:
            return {"success": False, "error": "Could not extract any text from the image."}
        
        return {"success": True, "question": extracted_text}

    except Exception as e:
        logger.error(f"An error occurred during image processing: {e}")
        return {"success": False, "error": f"An error occurred during image processing: {e}"}

    
# Initialize the solver
math_solver = JEEMathSolver()

# --------- App Routes ----------
@app.route('/')
def index():
    """Main page with question input form"""
    return render_template('index.html')

@app.route('/solve', methods=['POST'])
def solve_problem():
    """Handle problem solving request from text or image."""
    try:
        question = request.form.get('question', '').strip()
        image_file = request.files.get('image_file')

        if not question and not image_file:
            flash('Please enter a math question or upload an image.', 'error')
            return redirect(url_for('index'))

        # If an image is uploaded, process it first
        if image_file:
            image_result = solve_problem_from_image(image_file)
            if not image_result['success']:
                flash(f"Error processing image: {image_result['error']}", 'error')
                return redirect(url_for('index'))
            
            question = image_result['question']
            
        # Validate that the final question looks like a math question
        if len(question) < 10:
            flash('Please enter a complete math question.', 'error')
            return redirect(url_for('index'))
            
        # Solve the problem with the text question (either from form or image)
        result = math_solver.solve_problem(question)
        
        if result['success']:
            raw_html = markdown.markdown(result['raw_response'], extensions=['extra', 'codehilite'])
            
            return render_template('solution.html', 
                                 solution=result['solution'],
                                 raw_response_html=raw_html,
                                 timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        else:
            flash(f"Error solving problem: {result['error']}", 'error')
            return redirect(url_for('index'))
            
    except Exception as e:
        logger.error(f"Error in solve_problem route: {e}")
        flash('An unexpected error occurred. Please try again.', 'error')
        return redirect(url_for('index'))

@app.route('/api/solve', methods=['POST'])
def api_solve():
    """API endpoint for solving problems (JSON response)"""
    try:
        data = request.get_json()
        
        if not data or 'question' not in data:
            return jsonify({'error': 'Question is required'}), 400
        
        question = data['question'].strip()
        
        if not question:
            return jsonify({'error': 'Question cannot be empty'}), 400
        
        result = math_solver.solve_problem(question)
        
        if result['success']:
            return jsonify({
                'success': True,
                'solution': result['solution'].dict(),
                'raw_response': result['raw_response']
            })
        else:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 500
            
    except Exception as e:
        logger.error(f"Error in API solve: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'JEE Math Solver'})

@app.errorhandler(404)
def not_found(error):
    return render_template('error.html', error_message="Page not found"), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html', error_message="Internal server error"), 500

if __name__ == '__main__':
    # Check if required environment variables are set
    if not os.getenv('GEMINI_API_KEY'):
        logger.error("GEMINI_API_KEY not found in environment variables")
        print("Please set GEMINI_API_KEY in your .env file")
        exit(1)
    
    # Run the app
    debug_mode = os.getenv('DEBUG', 'False').lower() == 'true'
    port = int(os.getenv('PORT', 5000))
    
    print(f"Starting JEE Mains Math Solver on port {port}")
    print("Make sure your .env file contains GEMINI_API_KEY")
    
    app.run(debug=debug_mode, host='0.0.0.0', port=port)