from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..models import QuestionSet, Question, db
from ..utils import process_options
import json

questions_bp = Blueprint('questions', __name__)

@questions_bp.route('/api/question-sets', methods=['GET'])
@jwt_required()
def get_question_sets():
    current_user_id = get_jwt_identity()
    sets = QuestionSet.query.filter_by(user_id=int(current_user_id)).all()
    return jsonify([{
        'id': s.id,
        'name': s.name,
        'created_at': s.created_at.isoformat(),
        'question_count': len(s.questions)
    } for s in sets]), 200

@questions_bp.route('/api/question-sets/<int:set_id>', methods=['DELETE'])
@jwt_required()
def delete_set(set_id):
    current_user_id = get_jwt_identity()
    question_set = QuestionSet.query.filter_by(id=set_id, user_id=int(current_user_id)).first()
    
    if not question_set:
        return jsonify({'error': 'Question set not found'}), 404
    
    try:
        db.session.delete(question_set)
        db.session.commit()
        return jsonify({'message': 'Question set deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@questions_bp.route('/api/question-sets/<int:set_id>/name', methods=['PUT'])
@jwt_required()
def update_set_name(set_id):
    current_user_id = get_jwt_identity()
    data = request.get_json()
    
    if 'name' not in data:
        return jsonify({'error': 'New name is required'}), 400
    
    question_set = QuestionSet.query.filter_by(id=set_id, user_id=int(current_user_id)).first()
    
    if not question_set:
        return jsonify({'error': 'Question set not found'}), 404
    
    try:
        question_set.name = data['name']
        db.session.commit()
        return jsonify({
            'message': 'Question set name updated successfully',
            'id': question_set.id,
            'name': question_set.name
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@questions_bp.route('/api/questions', methods=['POST'])
@jwt_required()
def upload_questions():
    current_user_id = get_jwt_identity()
    data = request.get_json()
    
    if not all(key in data for key in ['name', 'questions']):
        return jsonify({'error': 'Missing required fields'}), 400
    
    try:
        # Create new question set
        question_set = QuestionSet(name=data['name'], user_id=int(current_user_id))
        db.session.add(question_set)
        db.session.commit()
        
        # Add questions to the set
        for q in data['questions']:
            if not all(key in q for key in ['question', 'options', 'correct_answer']):
                return jsonify({'error': 'Invalid question format'}), 400
            
            options_json = process_options(q['options'])
            question = Question(
                question_text=q['question'],
                options=options_json,
                correct_answer=q['correct_answer'],
                set_id=question_set.id
            )
            db.session.add(question)
        
        db.session.commit()
        return jsonify({
            'message': 'Questions uploaded successfully',
            'set_id': question_set.id
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

def save_question(question_data, set_id):
    """Save a question to the database with properly formatted options"""
    if not all(key in question_data for key in ['question', 'options', 'correct_answer']):
        raise ValueError('Invalid question format')
    
    options_json = process_options(question_data['options'])
    question = Question(
        question_text=question_data['question'],
        options=options_json,
        correct_answer=question_data['correct_answer'],
        set_id=set_id
    )
    db.session.add(question)
    return question
