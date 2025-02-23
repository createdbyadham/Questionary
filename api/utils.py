import os
import shutil
import time
import json
from mcq_extractor import MCQExtractor
from flask import current_app
from .models import QuestionSet, Question, db

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
        (info.get('completed', False) and info.get('timestamp', 0) + 60 < current_time)
    ]
    for session_id in expired_sessions:
        del progress_info[session_id]

def cleanup_temp_files(temp_folder, upload_folder):
    """Clean up old files in temp and uploads directories"""
    current_time = time.time()
    for directory in [temp_folder, upload_folder]:
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
            'message': 'Starting file processing...',
            'percent': 0,
            'completed': False,
            'questions_saved': False
        })
        
        # Create a temporary copy of the file
        temp_file = f"{file_path}.temp"
        shutil.copy2(file_path, temp_file)
        print(f"Created temporary PDF: {temp_file}")
        progress_info[session_id].update({
            'message': 'Extracting text from PDF...',
            'percent': 10
        })
        
        try:
            # Extract text from PDF
            pdf_text = mcq_extractor.extract_text_from_pdf(temp_file)
            if not pdf_text.strip():
                raise Exception("No text could be extracted from the PDF file")
            
            progress_info[session_id].update({
                'message': 'Text extracted successfully. Processing questions...',
                'percent': 20
            })
            
            # Extract questions using AI
            def progress_callback(message, current, total):
                percent = 20 + (current / total * 60)  # Scale to 20-80%
                progress_info[session_id].update({
                    'message': f'Processing questions: {message}',
                    'percent': percent
                })
            
            mcq_extractor.set_progress_callback(progress_callback)
            result = mcq_extractor.process_file(temp_file)
            
            if not result or not result.get('questions'):
                raise Exception("No questions were extracted from the file")
            
            # Save questions to database within app context
            progress_info[session_id].update({
                'message': 'Questions extracted. Saving to database...',
                'percent': 80
            })
            
            with current_app.app_context():
                # Create new question set
                question_set = QuestionSet(name=set_name, user_id=progress_info[session_id].get('user_id'))
                db.session.add(question_set)
                db.session.commit()
                
                # Add questions to the set
                total_questions = len(result['questions'])
                for i, q in enumerate(result['questions']):
                    options_json = process_options(q['options'])
                    question = Question(
                        question_text=q['question'],
                        options=options_json,
                        correct_answer=q['correct_answer'],
                        set_id=question_set.id
                    )
                    db.session.add(question)
                    
                    # Update progress for database saving
                    progress_info[session_id].update({
                        'message': f'Saving questions to database ({i + 1}/{total_questions})...',
                        'percent': 80 + ((i + 1) / total_questions * 20)  # Scale from 80-100%
                    })
                
                db.session.commit()
                
                progress_info[session_id].update({
                    'status': 'completed',
                    'message': f'Successfully processed {total_questions} questions',
                    'percent': 100,
                    'completed': True,
                    'questions_saved': True,
                    'set_id': question_set.id
                })
            
        except Exception as e:
            print(f"Error in process_file: {str(e)}")
            progress_info[session_id].update({
                'status': 'error',
                'message': str(e),
                'percent': 0,
                'completed': True,
                'error': True
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
            'percent': 0,
            'completed': True,
            'error': True
        })
    finally:
        # Clean up original file
        cleanup_file(file_path)
        print(f"Cleaned up file: {file_path}")

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