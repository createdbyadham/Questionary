import os
from openai import OpenAI
import json
from typing import List, Dict, Union, Callable, Tuple
import PyPDF2
import re
import time
import concurrent.futures
from tqdm import tqdm
from dotenv import load_dotenv
from PyPDF2 import PdfReader

class MCQGenerator:
    def __init__(self):
        load_dotenv()
        self.client = OpenAI(
            base_url="https://models.inference.ai.azure.com",
            api_key=os.getenv('GITHUB_TOKEN')
        )
        self.progress_callback = None
        self.current_progress = 0
        self.total_progress = 0
        self.max_workers = 5  # Number of parallel workers

    def set_progress_callback(self, callback):
        self.progress_callback = callback

    def update_progress(self, status: str, current: int, total: int):
        self.current_progress = current
        self.total_progress = total
        if self.progress_callback:
            self.progress_callback(status, current, total)

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from PDF file."""
        try:
            print(f"Processing PDF file: {pdf_path}")
            reader = PdfReader(pdf_path)
            text_with_pages = []
            page_numbers = []
            
            for i, page in enumerate(reader.pages):
                text = page.extract_text()
                if text.strip():
                    text_with_pages.append(text)
                    page_numbers.extend([i + 1] * len(text.split()))  # Track page number for each word
            
            full_text = " ".join(text_with_pages)
            
            # Clean up common PDF extraction issues
            full_text = re.sub(r'\f', '\n', full_text)
            full_text = re.sub(r'(?<!\n)\n(?!\n)', ' ', full_text)
            full_text = re.sub(r'\s+', ' ', full_text)
            full_text = re.sub(r'\n{3,}', '\n\n', full_text)
            full_text = full_text.strip()
            
            return full_text
        except Exception as e:
            print(f"Error in extract_text_from_pdf: {str(e)}")
            raise Exception(f"Error reading PDF: {str(e)}")

    def chunk_text(self, text: str, chunk_size: int = 2000) -> List[str]:
        """Split text into chunks of approximately equal size."""
        words = text.split()
        chunks = []
        current_chunk = []
        current_length = 0
        
        for word in words:
            word_length = len(word) + 1  # +1 for space
            if current_length + word_length > chunk_size and current_chunk:
                chunks.append(' '.join(current_chunk))
                current_chunk = [word]
                current_length = word_length
            else:
                current_chunk.append(word)
                current_length += word_length
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks

    def generate_mcqs_from_chunk(self, chunk: str, num_questions: int, lecture_name: str, page_range: str) -> List[Dict]:
        """Generate MCQs from a text chunk using GPT-4."""
        system_prompt = """You are an expert at generating multiple choice questions from text and formatting them as JSON. For each question:
1. Create clear, concise questions that test understanding
2. Generate 4 distinct options for each question
3. Ensure correct_answer matches one of the options exactly
4. Include source and page information in the output
5. Output only valid JSON in the specified format"""

        user_prompt = f"""Generate {num_questions} multiple choice questions from this text:

{chunk}

Output in this exact JSON format:
{{
    "questions": [
        {{
            "question": "question text here",
            "options": [
                "option 1 text",
                "option 2 text",
                "option 3 text",
                "option 4 text"
            ],
            "correct_answer": "correct option text here",
            "source_lecture": "{lecture_name}",
            "page_range": "{page_range}"
        }}
    ]
}}"""

        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                response = self.client.chat.completions.create(
                    messages=[
                        {
                            "role": "system",
                            "content": system_prompt,
                        },
                        {
                            "role": "user",
                            "content": user_prompt,
                        }
                    ],
                    model="gpt-4o",
                    temperature=0.1,
                    max_tokens=4096,
                    top_p=1
                )
                
                result = response.choices[0].message.content.strip()
                print(f"\nAPI Response:\n{result}\n")  # Debug print
                
                # Remove markdown and clean response
                result = re.sub(r'^```json\s*|\s*```$', '', result).strip()
                
                if not (result.startswith('{') and result.endswith('}')):
                    print("Response is not a JSON object")
                    retry_count += 1
                    continue
                    
                try:
                    parsed = json.loads(result)
                    if "questions" not in parsed:
                        print("No 'questions' key in parsed JSON")
                        retry_count += 1
                        continue
                        
                    questions = parsed["questions"]
                    if not questions:
                        print("Empty questions list")
                        retry_count += 1
                        continue
                        
                    # Validate each question
                    valid_questions = []
                    for q in questions:
                        try:
                            if not all(key in q for key in ["question", "options", "correct_answer"]):
                                print(f"Missing required keys in question: {q}")
                                continue
                            if q["correct_answer"] not in q["options"]:
                                print(f"Correct answer not in options: {q}")
                                continue
                                
                            # Add source and page info if missing
                            q["source_lecture"] = lecture_name
                            q["page_range"] = page_range
                            valid_questions.append(q)
                        except Exception as e:
                            print(f"Error validating question: {str(e)}")
                            continue
                            
                    if valid_questions:
                        return valid_questions
                    else:
                        print("No valid questions found in response")
                        retry_count += 1
                        continue
                    
                except json.JSONDecodeError as e:
                    print(f"JSON decode error: {str(e)}")
                    print(f"Raw response: {result}")
                    retry_count += 1
                    continue
                    
            except Exception as e:
                print(f"API error: {str(e)}")
                retry_count += 1
                time.sleep(1)  # Add a small delay between retries
                continue
        
        print(f"Failed to generate valid questions after {max_retries} attempts")
        return []  # Return empty list instead of raising exception

    def process_lecture(self, file_path: str, questions_per_chunk: int = 2) -> List[Dict]:
        """Process a single lecture file and generate questions."""
        try:
            lecture_name = os.path.basename(file_path)
            text = self.extract_text_from_pdf(file_path)
            chunks = self.chunk_text(text)
            
            # Calculate how many chunks we need to process to get the desired number of questions
            total_questions_needed = questions_per_chunk
            questions_per_chunk_adjusted = max(1, total_questions_needed // len(chunks))
            remaining_questions = total_questions_needed % len(chunks)
            
            all_questions = []
            total_chunks = len(chunks)
            
            for i, chunk in enumerate(chunks):
                if len(all_questions) >= total_questions_needed:
                    break
                    
                # Add an extra question to some chunks if we need to distribute remaining questions
                current_chunk_questions = questions_per_chunk_adjusted
                if remaining_questions > 0:
                    current_chunk_questions += 1
                    remaining_questions -= 1
                
                # Determine page range for this chunk
                chunk_words = chunk.split()
                start_page = 1
                end_page = 1
                page_range = f"{start_page}-{end_page}" if start_page != end_page else str(start_page)
                
                self.update_progress(f"Generating questions from {lecture_name}", i + 1, total_chunks)
                
                try:
                    questions = self.generate_mcqs_from_chunk(
                        chunk,
                        current_chunk_questions,
                        lecture_name,
                        page_range
                    )
                    if questions:  # Only extend if we got valid questions
                        all_questions.extend(questions)
                except Exception as e:
                    print(f"Error processing chunk {i + 1}: {str(e)}")
                    # Continue with next chunk instead of failing completely
                    continue
            
            if not all_questions:
                raise Exception("No questions were generated from any chunks")
                
            return all_questions
            
        except Exception as e:
            print(f"Error processing lecture {file_path}: {str(e)}")
            raise  # Re-raise the exception to be handled by the caller

    def generate_mcqs(self, file_paths: List[str], total_questions: int) -> List[Dict]:
        """Generate MCQs from multiple lecture files."""
        all_questions = []
        total_files = len(file_paths)
        
        # Calculate questions per file and per chunk
        questions_per_file = max(1, total_questions // total_files)
        estimated_chunks_per_file = 5  # This is an estimate, adjust based on average file size
        questions_per_chunk = max(1, questions_per_file // estimated_chunks_per_file)
        
        for i, file_path in enumerate(file_paths):
            self.update_progress(f"Processing lecture {i + 1}/{total_files}", i, total_files)
            questions = self.process_lecture(file_path, questions_per_chunk)
            all_questions.extend(questions)
        
        # If we generated more questions than requested, randomly select the desired number
        if len(all_questions) > total_questions:
            import random
            all_questions = random.sample(all_questions, total_questions)
        
        return all_questions
