from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..models import QuestionSet, Question, db
import json
import random

quiz_bp = Blueprint('quiz', __name__)

@quiz_bp.route('/api/get_quiz', methods=['POST'])
@jwt_required()
def get_quiz():
    current_user_id = get_jwt_identity()
    data = request.get_json()
    
    print("Quiz request data:", data)  # Debug log
    
    if not data or 'selected_sets' not in data:
        return jsonify({'error': 'No question sets selected'}), 400
        
    selected_sets = data['selected_sets']
    questions_per_quiz = data.get('questions_per_quiz', 40)
    
    # Get all questions from selected sets that belong to the user
    questions = []
    for set_id in selected_sets:
        print(f"Fetching questions for set {set_id}")  # Debug log
        question_set = QuestionSet.query.filter_by(id=set_id, user_id=int(current_user_id)).first()
        if question_set:
            print(f"Found set {set_id} with {len(question_set.questions)} questions")  # Debug log
            for q in question_set.questions:
                try:
                    options = json.loads(q.options) if isinstance(q.options, str) else q.options
                    print(f"Question {q.id} options:", options)  # Debug log
                    questions.append({
                        'id': q.id,
                        'question': q.question_text,
                        'options': options,
                        'set_id': q.set_id
                    })
                except Exception as e:
                    print(f"Error processing question {q.id}:", str(e))  # Debug log
                    continue
    
    if not questions:
        return jsonify({'error': 'No questions found in selected sets'}), 404
    
    print(f"Total questions before shuffle: {len(questions)}")  # Debug log
    
    # Shuffle questions and limit to requested number
    random.shuffle(questions)
    questions = questions[:questions_per_quiz]
    
    print(f"Returning {len(questions)} questions")  # Debug log
    print("First question sample:", questions[0] if questions else None)  # Debug log
    
    # Shuffle options for each question
    for q in questions:
        random.shuffle(q['options'])
    
    return jsonify(questions)

@quiz_bp.route('/api/quiz/check', methods=['POST'])
@jwt_required()
def check_answer():
    data = request.get_json()
    
    print("Check answer request data:", data)  # Debug log
    
    if not all(key in data for key in ['question_id', 'answer']):
        return jsonify({'error': 'Missing required fields'}), 400
    
    question = Question.query.get(data['question_id'])
    if not question:
        return jsonify({'error': 'Question not found'}), 404
    
    print(f"Checking answer for question {data['question_id']}")  # Debug log
    
    is_correct = data['answer'] == question.correct_answer
    return jsonify({
        'correct': is_correct,
        'correct_answer': question.correct_answer
    }), 200

@quiz_bp.route('/api/submit_quiz', methods=['POST'])
@jwt_required()
def submit_quiz():
    data = request.get_json()
    
    print("Submit quiz request data:", data)  # Debug log
    
    if not all(key in data for key in ['set_id', 'answers']):
        return jsonify({'error': 'Missing required fields'}), 400
    
    current_user_id = get_jwt_identity()
    question_set = QuestionSet.query.filter_by(id=data['set_id'], user_id=current_user_id).first()
    
    if not question_set:
        return jsonify({'error': 'Question set not found'}), 404
    
    print(f"Processing quiz submission for set {data['set_id']}")  # Debug log
    
    results = []
    correct_count = 0
    total_questions = len(question_set.questions)
    
    # Process each answer
    for answer in data['answers']:
        print(f"Processing answer for question {answer['question_id']}")  # Debug log
        
        if not all(key in answer for key in ['question_id', 'selected_answer']):
            return jsonify({'error': 'Invalid answer format'}), 400
        
        question = Question.query.get(answer['question_id'])
        if not question or question.set_id != question_set.id:
            return jsonify({'error': f'Question {answer["question_id"]} not found in set'}), 404
        
        is_correct = answer['selected_answer'] == question.correct_answer
        if is_correct:
            correct_count += 1
        
        results.append({
            'question_id': question.id,
            'question_text': question.question_text,
            'selected_answer': answer['selected_answer'],
            'correct_answer': question.correct_answer,
            'is_correct': is_correct
        })
    
    print(f"Quiz submission results: {results}")  # Debug log
    
    # Calculate score
    score = (correct_count / total_questions) * 100 if total_questions > 0 else 0
    
    return jsonify({
        'score': score,
        'correct_count': correct_count,
        'total_questions': total_questions,
        'results': results
    }), 200

@quiz_bp.route('/api/quiz/review/<int:set_id>', methods=['GET'])
@jwt_required()
def review_incorrect(set_id):
    current_user_id = get_jwt_identity()
    question_set = QuestionSet.query.filter_by(id=set_id, user_id=current_user_id).first()
    
    if not question_set:
        return jsonify({'error': 'Question set not found'}), 404
    
    print(f"Fetching questions for review in set {set_id}")  # Debug log
    
    questions = []
    for q in question_set.questions:
        question_dict = {
            'id': q.id,
            'question': q.question_text,
            'options': json.loads(q.options),
            'correct_answer': q.correct_answer
        }
        questions.append(question_dict)
    
    return jsonify({
        'set_id': set_id,
        'name': question_set.name,
        'questions': questions
    }), 200

@quiz_bp.route('/api/submit_review', methods=['POST'])
@jwt_required()
def submit_review():
    data = request.get_json()
    
    print("Submit review request data:", data)  # Debug log
    
    if not all(key in data for key in ['set_id', 'reviews']):
        return jsonify({'error': 'Missing required fields'}), 400
    
    current_user_id = get_jwt_identity()
    question_set = QuestionSet.query.filter_by(id=data['set_id'], user_id=current_user_id).first()
    
    if not question_set:
        return jsonify({'error': 'Question set not found'}), 404
    
    print(f"Processing review submission for set {data['set_id']}")  # Debug log
    
    results = []
    for review in data['reviews']:
        print(f"Processing review for question {review['question_id']}")  # Debug log
        
        if not all(key in review for key in ['question_id', 'understood']):
            return jsonify({'error': 'Invalid review format'}), 400
        
        question = Question.query.get(review['question_id'])
        if not question or question.set_id != question_set.id:
            return jsonify({'error': f'Question {review["question_id"]} not found in set'}), 404
        
        results.append({
            'question_id': question.id,
            'question_text': question.question_text,
            'understood': review['understood']
        })
    
    print(f"Review submission results: {results}")  # Debug log
    
    return jsonify({
        'message': 'Review submitted successfully',
        'results': results
    }), 200
