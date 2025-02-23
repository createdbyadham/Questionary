from dotenv import load_dotenv
load_dotenv()

from flask import Flask, jsonify, request, session
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import os
from mcq_extractor import MCQExtractor
import json
import threading
from queue import Queue
import shutil
import time
import uuid
from flask_sqlalchemy import SQLAlchemy
import random

app = Flask(__name__)
CORS(app, supports_credentials=True)  # Enable credentials for sessions
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-here')  # Set a secret key for sessions
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # Allow session cookies in cross-origin requests
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads')
app.config['TEMP_FOLDER'] = os.path.join(os.getcwd(), 'temp')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///questions.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Ensure necessary directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['TEMP_FOLDER'], exist_ok=True)

# Initialize MCQ extractor
mcq_extractor = MCQExtractor()

# Store progress information with TTL
progress_info = {}
PROGRESS_TTL = 3600  # 1 hour in seconds

def cleanup_file(filepath: str):
    """Safely clean up a file."""
    try:
        if os.path.exists(filepath):
            try:
                if os.path.isfile(filepath):
                    os.remove(filepath)
                elif os.path.isdir(filepath):
                    shutil.rmtree(filepath, ignore_errors=True)
            except PermissionError:
                print(f"Permission denied when cleaning up {filepath} - will be cleaned up later")
            except Exception as e:
                print(f"Error cleaning up {filepath}: {str(e)}")
    except Exception as e:
        print(f"Error checking file {filepath}: {str(e)}")

def cleanup_old_progress():
    """Clean up progress info older than TTL"""
    current_time = time.time()
    expired_sessions = [
        session_id for session_id, info in progress_info.items()
        if info.get('timestamp', 0) + PROGRESS_TTL < current_time or
        (info.get('completed', False) and info.get('timestamp', 0) + 60 < current_time)  # Remove completed sessions after 1 minute
    ]
    for session_id in expired_sessions:
        del progress_info[session_id]

def cleanup_temp_files():
    """Clean up old files in temp and uploads directories"""
    current_time = time.time()
    for directory in [app.config['TEMP_FOLDER'], app.config['UPLOAD_FOLDER']]:
        try:
            if not os.path.exists(directory):
                continue
                
            for filename in os.listdir(directory):
                try:
                    filepath = os.path.join(directory, filename)
                    try:
                        if os.path.getctime(filepath) + PROGRESS_TTL < current_time:
                            cleanup_file(filepath)
                    except OSError:
                        # If we can't get creation time, try to clean up anyway
                        cleanup_file(filepath)
                except Exception as e:
                    print(f"Error processing file {filename}: {str(e)}")
        except Exception as e:
            print(f"Error accessing directory {directory}: {str(e)}")

def process_file_async(file_path: str, session_id: str):
    """Process file asynchronously and clean up afterwards."""
    try:
        print(f"\nProcessing PDF file: {file_path}")
        
        # Get the set name from progress info
        set_name = progress_info[session_id].get('set_name', 'Unnamed Set')
        
        # Initialize progress
        progress_info[session_id].update({
            'status': 'processing',
            'message': 'Starting processing...',
            'percent': 0,
            'completed': False,
            'questions_saved': False
        })
        
        # Create a temporary copy of the file
        temp_file = f"{file_path}.temp"
        shutil.copy2(file_path, temp_file)
        print(f"Created temporary PDF: {temp_file}")
        
        try:
            # Extract text from PDF
            pdf_text = mcq_extractor.extract_text_from_pdf(temp_file)
            progress_info[session_id].update({
                'message': 'Extracted text from PDF, processing questions...',
                'percent': 20
            })
            
            if not pdf_text.strip():
                raise Exception("No text could be extracted from the PDF file")
            
            # Extract questions using AI
            def progress_callback(message, current, total):
                percent = 20 + (current / total * 60)  # Scale to 20-80%
                progress_info[session_id].update({
                    'message': message,
                    'percent': percent
                })
            
            mcq_extractor.set_progress_callback(progress_callback)
            questions = mcq_extractor.extract_mcqs_with_ai(pdf_text)
            
            if not questions or not questions.get('questions'):
                raise Exception("No questions were extracted from the file")
            
            progress_info[session_id].update({
                'message': 'Saving questions to database...',
                'percent': 80
            })
            
            # Save questions to database with the set name
            question_set = QuestionSet(name=set_name)
            db.session.add(question_set)
            db.session.commit()  # Commit to get the question_set.id
            
            for q in questions['questions']:
                # Ensure options is a JSON string array
                options_json = process_options(q['options'])
                question = Question(
                    question_text=q['question'],
                    options=options_json,
                    correct_answer=q['correct_answer'],
                    set_id=question_set.id
                )
                db.session.add(question)
            
            db.session.commit()
            print(f"Saved {len(questions['questions'])} questions to database with set name: {set_name}")
            
            # Update progress with success
            progress_info[session_id].update({
                'status': 'complete',
                'message': f'Successfully processed {len(questions["questions"])} questions',
                'questions': questions['questions'],
                'completed': True,
                'questions_saved': True,
                'percent': 100
            })
            
        except Exception as e:
            print(f"Error processing file: {str(e)}")
            progress_info[session_id].update({
                'status': 'error',
                'message': str(e),
                'error': str(e),
                'completed': True,
                'percent': 100
            })
            raise
        finally:
            # Clean up temporary file
            cleanup_file(temp_file)
            print(f"Cleaned up temporary PDF: {temp_file}")
            
    except Exception as e:
        print(f"Error in process_file_async: {str(e)}")
        progress_info[session_id].update({
            'status': 'error',
            'message': str(e),
            'error': str(e),
            'completed': True,
            'percent': 100
        })
    finally:
        # Clean up original file
        cleanup_file(file_path)

def process_options(options):
    """Process options to ensure they are stored in a consistent JSON format"""
    if isinstance(options, str):
        try:
            # Try to parse as JSON first
            parsed = json.loads(options)
            if isinstance(parsed, list):
                return json.dumps(parsed)
        except json.JSONDecodeError:
            # If it's not JSON, split by comma if present
            if ',' in options:
                option_list = [opt.strip() for opt in options.split(',')]
                return json.dumps(option_list)
            # If no comma, treat as single option
            return json.dumps([options])
    elif isinstance(options, list):
        return json.dumps(options)
    return json.dumps([])

@app.route('/')
def index():
    return "Hello, World!"

@app.route('/get_question_sets')
def get_question_sets():
    sets = QuestionSet.query.all()
    return jsonify([{'id': s.id, 'name': s.name, 'question_count': len(s.questions)} for s in sets])

@app.route('/upload', methods=['POST'])
def upload_questions():
    try:
        data = request.json
        set_name = data.get('set_name', 'Unnamed Set')
        questions_data = data.get('questions', [])
        
        if not questions_data:
            return jsonify({'error': 'No questions found in upload'}), 400
            
        # Create new question set
        question_set = QuestionSet(name=set_name)
        db.session.add(question_set)
        db.session.flush()  # This assigns an ID to question_set
            
        for q in questions_data:
            options = process_options(q['options'])
            new_question = Question(
                question_text=q['question'],
                options=options,
                correct_answer=q['correct_answer'],
                set_id=question_set.id
            )
            db.session.add(new_question)
        
        db.session.commit()
        return jsonify({'message': f'Questions uploaded successfully to set: {set_name}'})
    except Exception as e:
        print("Error:", str(e))
        return jsonify({'error': str(e)}), 400

@app.route('/upload_file', methods=['POST'])
def upload_file():
    """Handle file upload and start processing."""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Get the set name from the form data
        set_name = request.form.get('set_name', '').strip()
        if not set_name:
            # Use the filename without extension as the default set name
            set_name = os.path.splitext(secure_filename(file.filename))[0]
        
        # Check if it's a JSON file
        if file.filename.endswith('.json'):
            try:
                # Read and validate JSON content
                json_data = json.loads(file.read().decode('utf-8'))
                
                if not isinstance(json_data, dict) or 'questions' not in json_data:
                    return jsonify({'error': 'Invalid JSON format. Must contain a "questions" array'}), 400
                
                questions = json_data['questions']
                if not isinstance(questions, list):
                    return jsonify({'error': 'Questions must be an array'}), 400
                
                # Validate each question
                for q in questions:
                    if not all(k in q for k in ('question', 'options', 'correct_answer')):
                        return jsonify({'error': 'Each question must have question, options, and correct_answer'}), 400
                    if not isinstance(q['options'], list):
                        return jsonify({'error': 'Options must be an array'}), 400
                    if q['correct_answer'] not in q['options']:
                        return jsonify({'error': 'Correct answer must be one of the options'}), 400
                
                # Save questions to database
                question_set = QuestionSet(name=set_name)
                db.session.add(question_set)
                db.session.commit()
                
                for q in questions:
                    options_json = json.dumps(q['options'])
                    question = Question(
                        question_text=q['question'],
                        options=options_json,
                        correct_answer=q['correct_answer'],
                        set_id=question_set.id
                    )
                    db.session.add(question)
                
                db.session.commit()
                return jsonify({
                    'message': f'Successfully imported {len(questions)} questions from JSON',
                    'questions_imported': len(questions)
                })
                
            except json.JSONDecodeError:
                return jsonify({'error': 'Invalid JSON file'}), 400
            except Exception as e:
                return jsonify({'error': f'Error processing JSON: {str(e)}'}), 400
        
        # If not JSON, process as PDF
        if not file.filename.endswith('.pdf'):
            return jsonify({'error': 'Only PDF and JSON files are supported'}), 400
            
        # Generate a unique session ID
        session_id = str(uuid.uuid4())
        
        # Save the file
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['TEMP_FOLDER'], f"{session_id}_{filename}")
        file.save(file_path)
        print(f"File saved successfully to: {file_path}")
        
        # Initialize progress tracking with set name and timestamp
        progress_info[session_id] = {
            'status': 'processing',
            'message': 'Starting processing...',
            'percent': 0,
            'set_name': set_name,
            'timestamp': time.time(),
            'completed': False,
            'error': None,
            'file_path': file_path
        }
        print(f"Initialized progress tracking for session {session_id}")
        
        # Start processing in a background thread
        thread = threading.Thread(target=process_file_async, args=(file_path, session_id))
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'message': 'File upload started',
            'session_id': session_id
        })
        
    except Exception as e:
        print(f"Error in upload_file: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/get_progress/<session_id>', methods=['GET'])
def get_progress(session_id):
    """Get the current progress of file processing."""
    try:
        cleanup_old_progress()  # Clean up old progress info
        
        if session_id not in progress_info:
            print(f"Session {session_id} not found in progress_info")
            print(f"Available sessions: {list(progress_info.keys())}")
            return jsonify({
                'status': 'error',
                'message': 'Session not found or expired',
                'percent': 0
            }), 404
        
        progress = progress_info[session_id]
        
        # Check if processing is complete
        if progress.get('completed', False):
            if progress.get('error'):
                return jsonify({
                    'status': 'error',
                    'message': progress['error'],
                    'percent': 100
                })
            else:
                return jsonify({
                    'status': 'completed',
                    'message': progress.get('message', 'Processing complete'),
                    'percent': 100
                })
        
        # Still processing
        return jsonify({
            'status': progress.get('status', 'processing'),
            'message': progress.get('message', 'Processing...'),
            'percent': progress.get('percent', 0)
        })
    except Exception as e:
        print(f"Error in get_progress: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'percent': 0
        }), 500

@app.route('/get_quiz', methods=['POST'])
def get_quiz():
    try:
        data = request.json
        selected_sets = data.get('selected_sets', [])
        questions_per_quiz = data.get('questions_per_quiz', 40)  # Default to 40 questions
        
        if not selected_sets:
            return jsonify({'error': 'No question sets selected'}), 400
        
        # Get questions from selected sets
        questions = Question.query.filter(Question.set_id.in_(selected_sets)).all()
        if not questions:
            return jsonify({'error': 'No questions found in selected sets'}), 404
        
        # Shuffle questions and limit to requested number
        total_questions = len(questions)
        num_questions = min(total_questions, questions_per_quiz)
        questions = random.sample(questions, num_questions)
        
        # Prepare questions for frontend and session
        quiz_questions = []
        for q in questions:
            options = json.loads(q.options)
            question_data = {
                'id': q.id,
                'question_text': q.question_text,
                'options': options,
                'set_id': q.set_id
            }
            quiz_questions.append(question_data)
            
        # Store minimal data in session
        session.clear()  # Clear any existing session data
        session['current_quiz'] = [{
            'id': q['id'],
            'correct_answer': Question.query.get(q['id']).correct_answer
        } for q in quiz_questions]
        session.modified = True
        
        print("Session after storing quiz:", session)
        print("Quiz questions stored:", quiz_questions)
        
        return jsonify(quiz_questions)
        
    except Exception as e:
        print("Error in get_quiz:", str(e))
        return jsonify({'error': str(e)}), 400

@app.route('/check_answer', methods=['POST'])
def check_answer():
    try:
        data = request.json
        question_id = data.get('question_id')
        selected_answer = data.get('selected_answer')
        
        question = Question.query.get(question_id)
        if not question:
            return jsonify({'error': 'Question not found'}), 404
            
        is_correct = selected_answer == question.correct_answer
        
        return jsonify({
            'is_correct': is_correct,
            'correct_answer': question.correct_answer
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/submit_quiz', methods=['POST'])
def submit_quiz():
    try:
        user_answers = request.json['answers']
        session_questions = session.get('current_quiz')
        
        if not session_questions:
            print("No quiz_questions in session:", session)
            return jsonify({'error': 'No quiz in progress'}), 400
        
        # Get full question data from database
        question_ids = [q['id'] for q in session_questions]
        full_questions = Question.query.filter(Question.id.in_(question_ids)).all()
        
        results = []
        correct_count = 0
        total_questions = len(session_questions)
        incorrect_answers = {}  # Changed to dict for frontend compatibility
        
        # Create a map of question data
        question_map = {str(q.id): q for q in full_questions}
        
        for sq in session_questions:
            question_id = str(sq['id'])
            user_answer = user_answers.get(question_id)
            full_q = question_map.get(question_id)
            
            if not full_q:
                continue
                
            options = json.loads(full_q.options)
            is_correct = user_answer == full_q.correct_answer
            
            if is_correct:
                correct_count += 1
            else:
                incorrect_answers[question_id] = {
                    'question': full_q.question_text,
                    'user_answer': user_answer,
                    'correct_answer': full_q.correct_answer,
                    'options': options
                }
            
            results.append({
                'question': full_q.question_text,
                'user_answer': user_answer,
                'correct_answer': full_q.correct_answer,
                'is_correct': is_correct,
                'options': options
            })
        
        # Store only minimal data in session
        session['review_questions'] = [{
            'id': q_id,
            'correct_answer': data['correct_answer']
        } for q_id, data in incorrect_answers.items()]
        session.modified = True
        
        return jsonify({
            'score': correct_count,
            'total': total_questions,
            'results': results,
            'incorrect_answers': incorrect_answers,
            'has_incorrect': len(incorrect_answers) > 0
        })
    except Exception as e:
        print("Submit quiz error:", str(e))
        return jsonify({'error': str(e)}), 400

@app.route('/review_incorrect', methods=['GET'])
def review_incorrect():
    try:
        review_questions = session.get('review_questions', [])
        if not review_questions:
            return jsonify({'error': 'No questions to review'}), 400

        print("Review questions from session:", review_questions)

        # Get full question data from database
        question_ids = [q['id'] for q in review_questions]
        full_questions = Question.query.filter(Question.id.in_(question_ids)).all()
        
        if not full_questions:
            return jsonify({'error': 'Could not find review questions'}), 404
        
        # Create review questions with full data
        review_data = []
        for q in full_questions:
            try:
                options = json.loads(q.options)  # Use json.loads instead of eval
                review_data.append({
                    'id': q.id,
                    'question_text': q.question_text,  # Match frontend expectation
                    'options': options,
                    'set_id': q.set_id
                })
            except Exception as e:
                print(f"Error processing question {q.id}: {str(e)}")
                continue
        
        if not review_data:
            return jsonify({'error': 'No valid questions to review'}), 400
            
        random.shuffle(review_data)
        print("Sending review data:", review_data)
        return jsonify(review_data)
        
    except Exception as e:
        print("Error in review_incorrect:", str(e))
        return jsonify({'error': str(e)}), 400

@app.route('/submit_review', methods=['POST'])
def submit_review():
    try:
        user_answers = request.json['answers']
        review_questions = session.get('review_questions', [])
        
        if not review_questions:
            return jsonify({'error': 'No review questions found'}), 400
        
        # Get full question data from database
        question_ids = [q['id'] for q in review_questions]
        full_questions = Question.query.filter(Question.id.in_(question_ids)).all()
        
        results = []
        correct_count = 0
        still_incorrect = []
        
        # Create a map of question data
        question_map = {str(q.id): q for q in full_questions}
        
        for rq in review_questions:
            question_id = str(rq['id'])
            user_answer = user_answers.get(question_id)
            full_q = question_map.get(question_id)
            
            if not full_q:
                continue
                
            options = json.loads(full_q.options)
            is_correct = user_answer == full_q.correct_answer
            
            if is_correct:
                correct_count += 1
            else:
                still_incorrect.append({
                    'id': full_q.id,
                    'correct_answer': full_q.correct_answer
                })
            
            results.append({
                'question': full_q.question_text,
                'user_answer': user_answer,
                'correct_answer': full_q.correct_answer,
                'is_correct': is_correct,
                'options': options
            })
        
        # Update session with remaining incorrect questions
        if still_incorrect:
            session['review_questions'] = still_incorrect
            session.modified = True
            return jsonify({
                'status': 'continue',
                'message': f'You still have {len(still_incorrect)} incorrect answers. Please click "Review Incorrect Answers" to try again.',
                'results': results,
                'total_questions': len(review_questions),
                'correct_count': correct_count,
                'score': (correct_count / len(review_questions)) * 100 if review_questions else 0
            })
        else:
            # Clear review questions from session when all are correct
            session.pop('review_questions', None)
            session.modified = True
            return jsonify({
                'status': 'complete',
                'message': 'Congratulations! You have correctly answered all questions.',
                'results': results,
                'total_questions': len(review_questions),
                'correct_count': correct_count,
                'score': 100.0
            })
            
    except Exception as e:
        print("Submit review error:", str(e))
        return jsonify({'error': str(e)}), 400

@app.route('/delete_set/<int:set_id>', methods=['POST'])
def delete_set(set_id):
    try:
        question_set = QuestionSet.query.get_or_404(set_id)
        db.session.delete(question_set)
        db.session.commit()
        return jsonify({'message': f'Question set "{question_set.name}" deleted successfully'})
    except Exception as e:
        db.session.rollback()
        print("Delete error:", str(e))
        return jsonify({'error': str(e)}), 400

@app.route('/update_set_name', methods=['POST'])
def update_set_name():
    """Update the name of an existing question set."""
    try:
        data = request.get_json()
        set_id = data.get('set_id')
        new_name = data.get('new_name', '').strip()

        if not set_id:
            return jsonify({'error': 'Set ID is required'}), 400
        if not new_name:
            return jsonify({'error': 'New name cannot be empty'}), 400

        # Find and update the question set
        question_set = QuestionSet.query.get(set_id)
        if not question_set:
            return jsonify({'error': 'Question set not found'}), 404

        question_set.name = new_name
        db.session.commit()

        return jsonify({
            'message': 'Set name updated successfully',
            'set_id': set_id,
            'new_name': new_name
        })

    except Exception as e:
        print(f"Error updating set name: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/quiz/<int:set_id>', methods=['GET'])
def get_quiz_api(set_id):
    try:
        questions = Question.query.filter_by(set_id=set_id).all()
        quiz_data = []
        
        for question in questions:
            quiz_data.append({
                'id': question.id,
                'question_text': question.question_text,
                'options': process_options(question.options),
                'correct_answer': question.correct_answer
            })
        
        return jsonify({'questions': quiz_data})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def save_question(question_data, set_id):
    """Save a question to the database with properly formatted options"""
    try:
        options = process_options(question_data['options'])
        question = Question(
            question_text=question_data['question'],
            options=options,
            correct_answer=question_data['correct_answer'],
            set_id=set_id
        )
        db.session.add(question)
        return True
    except Exception as e:
        print(f"Error saving question: {str(e)}")
        return False

db = SQLAlchemy(app)

class QuestionSet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    questions = db.relationship('Question', backref='question_set', cascade='all, delete-orphan', lazy=True)

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_text = db.Column(db.String(500), nullable=False)
    options = db.Column(db.String(500), nullable=False)  # Stored as JSON string
    correct_answer = db.Column(db.String(500), nullable=False)
    set_id = db.Column(db.Integer, db.ForeignKey('question_set.id'), nullable=False)

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True, port=5001)
