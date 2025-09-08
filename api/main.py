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
        """Solve the math problem using Gemini API"""
        try:
            # Create a prompt that explicitly requests a JSON object
            prompt = self.create_prompt(question)
            response = self.model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )

            if not response.text:
                raise Exception("No response generated from Gemini API")

            # The API is configured to return a JSON string, so we can parse it directly
            solution_data = json.loads(response.text)

            # Create validated response using Pydantic
            validated_solution = MathSolution(**solution_data)
        
            return {
                'success': True,
                'solution': validated_solution,
                'raw_response': response.text
            }
            
        except JSONDecodeError as e:
            logger.error(f"JSON decoding error: {e}")
            return {
                'success': False,
                'error': f"Failed to parse AI response as JSON: {e}",
                'raw_response': response.text if 'response' in locals() else None
            }
        except ValidationError as e:
            logger.error(f"Validation error: {e}")
            return {
                'success': False,
                'error': f"Response validation failed: {e}",
                'raw_response': response.text if 'response' in locals() else None
            }
        except Exception as e:
            logger.error(f"Error solving problem: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
# Initialize the solver
math_solver = JEEMathSolver()

# --------- App Routes ----------
@app.route('/')
def index():
    """Main page with question input form"""
    return render_template('index.html')

@app.route('/solve', methods=['POST'])
def solve_problem():
    """Handle problem solving request"""
    try:
        question = request.form.get('question', '').strip()
        
        if not question:
            flash('Please enter a math question to solve.', 'error')
            return redirect(url_for('index'))
        
        # Validate that input looks like a math question
        if len(question) < 10:
            flash('Please enter a complete math question.', 'error')
            return redirect(url_for('index'))
        
        # Solve the problem
        result = math_solver.solve_problem(question)
        
        if result['success']:
            # Convert markdown to HTML for better rendering
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