from flask import Flask, render_template, request, redirect, flash, jsonify, url_for
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

# Load environment variables from .env
load_dotenv()

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
        self.model = genai.GenerativeModel('gemini-1.5-flash',
            generation_config={"response_mime_type": "application/json"})

    def solve_problem(self, question):
        """
        Uses the Gemini model to solve a math problem and validate the response.
        """
        try:
            # Define the system instruction to act as an expert
            system_instruction = (
                "You are an expert in JEE Mains mathematics. Provide a step-by-step solution "
                "to the given math question. Your response MUST be in the following JSON format. "
                "Include the final answer, and an array of solution steps."
            )
            
            # The user prompt
            user_prompt = f"Solve the following JEE Mains math problem: {question}"

            # Generate content from the model
            response = self.model.generate_content(
                user_prompt,
                system_instruction=system_instruction
            )
            
            # Check for a valid response
            if not response.text:
                return {"success": False, "error": "AI did not provide a valid response."}

            try:
                # Attempt to parse the JSON response
                solution_data = json.loads(response.text)
                
                # Validate the solution data against the Pydantic model
                validated_solution = MathSolution(**solution_data)
                
                return {
                    "success": True,
                    "solution": validated_solution,
                    "raw_response": response.text
                }

            except (JSONDecodeError, ValidationError) as e:
                logger.error(f"Failed to parse or validate JSON response: {e}")
                return {
                    "success": False,
                    "error": f"The AI provided an invalid response format. Error: {e}"
                }

        except Exception as e:
            logger.error(f"An error occurred while calling the AI: {e}")
            return {"success": False, "error": f"An error occurred: {e}"}

math_solver = JEEMathSolver()

# Function to handle image-to-text conversion
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


# --------- App Routes ----------
@app.route('/')
def index():
    """Renders the main page with the problem input form."""
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
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=debug_mode, host='0.0.0.0', port=port)
