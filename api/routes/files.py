from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
import os
import uuid
import json
import shutil
import threading
import time
from ..models import QuestionSet, Question, db
from ..utils import mcq_extractor, mcq_generator, process_options

files_bp = Blueprint('files', __name__)

# Dictionary to store progress information
progress_info = {}

def process_file_async(app, file_path: str, session_id: str, user_id: str, model_type: str):
    """Process file asynchronously and clean up afterwards."""
    try:
        print(f"\nProcessing PDF file: {file_path}")
        
        # Get the set name and num_questions from progress info
        set_name = progress_info[session_id].get('set_name', 'Unnamed Set')
        num_questions = progress_info[session_id].get('num_questions', 10)  # Default to 10 if not specified
        
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
            processor = mcq_generator if model_type == 'generator' else mcq_extractor
            pdf_text = processor.extract_text_from_pdf(temp_file)
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
            
            processor.set_progress_callback(progress_callback)
            
            if model_type == 'generator':
                # Generator handles text extraction internally in process_lecture
                questions = {'questions': processor.process_lecture(temp_file, questions_per_chunk=num_questions)}
            else:
                # For extractor, we need to extract text first
                pdf_text = processor.extract_text_from_pdf(temp_file)
                if not pdf_text.strip():
                    raise Exception("No text could be extracted from the PDF file")
                questions = processor.extract_mcqs_with_ai(pdf_text)
            
            if not questions or not questions.get('questions'):
                raise Exception("No questions were extracted from the file")
            
            progress_info[session_id].update({
                'message': 'Saving questions to database...',
                'percent': 80
            })
            
            # Save questions to database with the set name and user_id within app context
            with app.app_context():
                question_set = QuestionSet(name=set_name, user_id=int(user_id))
                db.session.add(question_set)
                db.session.commit()
                
                for q in questions['questions']:
                    # Ensure options are stored as a JSON string
                    options = process_options(q['options'])
                    options_json = json.dumps(options) if isinstance(options, list) else options
                    
                    question = Question(
                        question_text=q['question'],
                        options=options_json,
                        correct_answer=q['correct_answer'],
                        set_id=question_set.id,
                        source_lecture=q.get('source_lecture', ''),
                        page_range=q.get('page_range', '')
                    )
                    db.session.add(question)
                
                db.session.commit()
                print(f"Saved {len(questions['questions'])} questions to database with set name: {set_name}")
                
                progress_info[session_id].update({
                    'status': 'complete',
                    'message': f'Successfully processed {len(questions["questions"])} questions',
                    'questions': questions['questions'],
                    'completed': True,
                    'questions_saved': True,
                    'set_id': question_set.id,
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

def cleanup_file(file_path):
    """Clean up a file if it exists."""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"Cleaned up file: {file_path}")
    except Exception as e:
        print(f"Error cleaning up file {file_path}: {str(e)}")

@files_bp.route('/api/upload-file', methods=['POST'])
@jwt_required()
def upload_file():
    """Handle file upload and start processing."""
    try:
        current_user_id = get_jwt_identity()
        
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Get the set name and model type from the form data
        set_name = request.form.get('set_name', '').strip()
        model_type = request.form.get('model_type', 'extractor')  # Default to extractor
        num_questions = int(request.form.get('num_questions', '10'))  # Get num_questions from form data
        
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
                question_set = QuestionSet(name=set_name, user_id=int(current_user_id))
                db.session.add(question_set)
                db.session.commit()
                
                for q in questions:
                    options_json = json.dumps(q['options'])
                    question = Question(
                        question_text=q['question'],
                        options=options_json,
                        correct_answer=q['correct_answer'],
                        set_id=question_set.id,
                        source_lecture=q.get('source_lecture', ''),
                        page_range=q.get('page_range', '')
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
        
        # Ensure TEMP_FOLDER exists
        temp_folder = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'temp')
        os.makedirs(temp_folder, exist_ok=True)
            
        # Generate a unique session ID
        session_id = str(uuid.uuid4())
        
        # Save the file
        filename = secure_filename(file.filename)
        file_path = os.path.join(temp_folder, f"{session_id}_{filename}")
        file.save(file_path)
        print(f"File saved successfully to: {file_path}")
        
        # Initialize progress tracking with set name and timestamp
        progress_info[session_id] = {
            'status': 'uploading',
            'message': 'File upload started...',
            'percent': 0,
            'set_name': set_name,
            'num_questions': num_questions,  # Store num_questions in progress info
            'model_type': model_type,
            'timestamp': time.time(),
            'completed': False,
            'error': None,
            'file_path': file_path
        }
        print(f"Initialized progress tracking for session {session_id}")
        
        # Get the current app
        from flask import current_app
        app = current_app._get_current_object()
        
        # Start processing in a separate thread
        thread = threading.Thread(target=process_file_async, args=(app, file_path, session_id, str(current_user_id), model_type))
        thread.start()
        
        return jsonify({
            'message': 'File upload started',
            'session_id': session_id
        }), 200
        
    except Exception as e:
        print(f"Error in upload_file: {str(e)}")
        return jsonify({'error': str(e)}), 500

@files_bp.route('/api/upload-progress/<session_id>', methods=['GET'])
@jwt_required()
def get_progress(session_id):
    """Get the progress of a file upload session."""
    if session_id not in progress_info:
        return jsonify({'error': 'Session not found'}), 404
        
    return jsonify(progress_info[session_id])
