import os
from openai import OpenAI
import json
from typing import List, Dict, Union, Callable, Tuple
import PyPDF2
import re
import time
import concurrent.futures
from tqdm import tqdm
import shutil
from dotenv import load_dotenv
from PyPDF2 import PdfReader

class MCQExtractor:
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
            text = extract_text(pdf_path)
            if not text.strip():
                raise Exception("No text could be extracted from the PDF file. The PDF might be scanned or have security restrictions.")
            
            # Clean up common PDF extraction issues
            text = re.sub(r'\f', '\n', text)  # Replace form feeds with newlines
            text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text)  # Join lines unless there's a double newline
            text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
            text = re.sub(r'\n{3,}', '\n\n', text)  # Normalize multiple newlines
            text = text.strip()
            
            return text
        except Exception as e:
            print(f"Error in extract_text_from_pdf: {str(e)}")
            raise Exception(f"Error reading PDF: {str(e)}")

    def clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        self.update_progress("Cleaning text", 0, 1)
        text = re.sub(r'\s+', ' ', text)
        text = text.replace('\n\n', '\n').strip()
        self.update_progress("Cleaning text", 1, 1)
        return text

    def chunk_text(self, text: str) -> List[str]:
        """Split text into chunks containing questions."""
        # More flexible question number patterns
        question_patterns = [
            r'\n\s*\d+[\.-]\s+',  # Standard numbered questions (1. or 1-)
            r'\n\s*Q\d+[\.-]\s+',  # Q1. or Q1-
            r'\n\s*Question\s+\d+[\.-]\s+',  # Question 1. or Question 1-
            r'\n\s*\(\d+\)\s+',  # (1) style
            r'\n\s*\[\d+\]\s+'  # [1] style
        ]
        
        # Try each pattern until we find questions
        questions = []
        for pattern in question_patterns:
            questions = [q.strip() for q in re.split(pattern, text) if q.strip()]
            if len(questions) > 1:  # Found questions with this pattern
                break
        
        if not questions:
            # If no patterns worked, try to split on double newlines and look for question-like content
            questions = [q.strip() for q in text.split('\n\n') if q.strip()]
            questions = [q for q in questions if re.search(r'(?:[A-D]\.|\(True/False\)|True\s*False)', q)]
        
        print(f"\nFound {len(questions)} potential questions")
        
        # Group questions into batches of 5 (smaller batches for better processing)
        batches = []
        current_batch = []
        for question in questions:
            current_batch.append(question)
            if len(current_batch) == 5:
                batches.append('\n'.join(current_batch))
                current_batch = []
        
        # Add any remaining questions
        if current_batch:
            batches.append('\n'.join(current_batch))
        
        print(f"Split text into {len(batches)} batches")
        return batches

    def process_batch(self, batch: str, batch_index: int, total_batches: int) -> Tuple[int, List[Dict]]:
        """Process a single batch of questions."""
        print(f"\nProcessing batch {batch_index + 1}/{total_batches}:")
        print(f"Batch content: {batch[:500]}...")

        system_prompt = """You are an expert at extracting multiple choice questions from text and formatting them as JSON. For each question:
1. Remove question numbers
2. Remove option letters (A,B,C,D)
3. Ensure correct_answer matches one of the options exactly
4. Handle both multiple choice (4 options) and True/False questions
5. Output only valid JSON in the specified format"""

        user_prompt = f"""Extract these multiple choice questions into JSON format with this exact structure:
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
            "correct_answer": "correct option text here"
        }}
    ]
}}

Questions to process:
{batch}"""

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
                
                ai_response = response.choices[0].message.content.strip()
                print(f"\nAI Response for batch {batch_index + 1}:")
                print(ai_response[:500])
                
                # Remove markdown and clean response
                ai_response = re.sub(r'^```json\s*|\s*```$', '', ai_response).strip()
                
                if not (ai_response.startswith('{') and ai_response.endswith('}')):
                    raise Exception("Response is not a JSON object")
                    
                chunk_questions = json.loads(ai_response)
                valid_questions = []
                
                if 'questions' in chunk_questions and chunk_questions['questions']:
                    for q in chunk_questions['questions']:
                        if (isinstance(q, dict) and 
                            'question' in q and 
                            'options' in q and 
                            'correct_answer' in q and 
                            isinstance(q['options'], list) and 
                            (len(q['options']) == 4 or  # Regular MCQ
                             (len(q['options']) == 2 and  # True/False question
                              all(opt.lower() in ['true', 'false'] for opt in q['options'])))):
                            
                            q['question'] = re.sub(r'^\d+[-\.]?\s*', '', q['question']).strip()
                            q['options'] = [re.sub(r'^[A-D]\.\s*', '', opt).strip() for opt in q['options']]
                            
                            if q['correct_answer'] in q['options']:
                                valid_questions.append(q)
                            else:
                                print(f"\nQuestion skipped - correct_answer not in options:")
                                print(f"Question: {q['question']}")
                                print(f"Options: {q['options']}")
                                print(f"Correct Answer: {q['correct_answer']}")
                        else:
                            print(f"\nInvalid question format:")
                            print(json.dumps(q, indent=2))
                
                if valid_questions:
                    print(f"Successfully extracted {len(valid_questions)} questions from batch {batch_index + 1}")
                    return batch_index, valid_questions
                
                print(f"No valid questions found in batch {batch_index + 1}")
                return batch_index, []
                
            except Exception as e:
                print(f"Error processing batch {batch_index + 1}: {str(e)}")
                retry_count += 1
                if retry_count < max_retries:
                    wait_time = 2 ** retry_count
                    print(f"Retrying batch {batch_index + 1} in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    print(f"Failed to process batch {batch_index + 1} after {max_retries} attempts")
                    return batch_index, []
        
        return batch_index, []

    def extract_mcqs_with_ai(self, text: str) -> Dict[str, List[Dict[str, Union[str, List[str], str]]]]:
        """Use GPT-4 to extract MCQs from text using parallel processing."""
        print("Starting MCQ extraction...")
        chunks = self.chunk_text(text)
        total_batches = len(chunks)
        all_questions = []
        processed_count = 0

        # Create a ThreadPoolExecutor for parallel processing
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all batches to the executor
            future_to_batch = {
                executor.submit(self.process_batch, chunk, i, total_batches): i 
                for i, chunk in enumerate(chunks)
            }

            # Process completed batches as they finish
            for future in concurrent.futures.as_completed(future_to_batch):
                batch_index, questions = future.result()
                all_questions.extend(questions)
                processed_count += 1
                
                # Update progress
                progress = (processed_count / total_batches) * 100
                self.update_progress(
                    f"Processed {processed_count}/{total_batches} batches ({progress:.1f}%)",
                    processed_count,
                    total_batches
                )

        if not all_questions:
            print("No questions were extracted from any batches")
            raise Exception("No valid questions could be extracted. Please ensure the PDF contains properly formatted multiple choice questions.")
            
        print(f"Successfully extracted a total of {len(all_questions)} questions")
        return {"questions": all_questions}

    def process_file(self, file_path: str) -> Dict[str, List[Dict[str, Union[str, List[str], str]]]]:
        """Process either PDF or text file and extract MCQs."""
        try:
            print(f"Starting to process file: {file_path}")
            if not os.path.exists(file_path):
                raise Exception(f"File not found: {file_path}")

            if file_path.lower().endswith('.pdf'):
                text = self.extract_text_from_pdf(file_path)
            else:
                self.update_progress("Reading text file", 0, 1)
                with open(file_path, 'r', encoding='utf-8') as file:
                    text = file.read()
                self.update_progress("Reading text file", 1, 1)

            text = self.clean_text(text)
            result = self.extract_mcqs_with_ai(text)

            self.update_progress("Saving results", 0, 1)
            output_path = os.path.join(os.path.dirname(file_path), 'parsed_questions.json')
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            self.update_progress("Saving results", 1, 1)

            return result

        except Exception as e:
            print(f"Error processing file: {str(e)}")
            return {"questions": []}

def extract_text(file_path):
    pdf_reader = PdfReader(file_path)
    text = ''
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text
