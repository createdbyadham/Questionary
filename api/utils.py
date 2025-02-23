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

def process_options(options):
    """Process options to ensure they are in a consistent format
    
    Args:
        options: Can be a string (JSON or newline-separated) or a list
        
    Returns:
        list: A list of options, ready to be JSON serialized before database storage
    """
    if isinstance(options, str):
        try:
            # Try to parse if it's a JSON string
            parsed = json.loads(options)
            return parsed if isinstance(parsed, list) else [parsed]
        except json.JSONDecodeError:
            # If not JSON, split by newlines and clean
            return [opt.strip() for opt in options.split('\n') if opt.strip()]
    elif isinstance(options, list):
        return options
    else:
        raise ValueError("Options must be either a JSON string or a list")