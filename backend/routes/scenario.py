from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Scenario

scenario_bp = Blueprint('scenario', __name__)

@scenario_bp.route('/', methods=['POST'])
@jwt_required()
def create_scenario():
    data = request.get_json()
    scenario = Scenario(
        name=data['name'],
        description=data.get('description', ''),
        data=data['data'],
        user_id=get_jwt_identity()
    )
    db.session.add(scenario)
    db.session.commit()
    return jsonify({'msg': 'Scenario created', 'id': scenario.id}), 201

@scenario_bp.route('/', methods=['GET'])
@jwt_required()
def list_scenarios():
    user_id = get_jwt_identity()
    scenarios = Scenario.query.filter_by(user_id=user_id).all()
    return jsonify([{
        'id': s.id,
        'name': s.name,
        'description': s.description,
        'data': s.data,
        'created_at': s.created_at
    } for s in scenarios]), 200

@scenario_bp.route('/<int:scenario_id>', methods=['GET'])
@jwt_required()
def get_scenario(scenario_id):
    scenario = Scenario.query.get_or_404(scenario_id)
    return jsonify({
        'id': scenario.id,
        'name': scenario.name,
        'description': scenario.description,
        'data': scenario.data,
        'created_at': scenario.created_at
    }), 200