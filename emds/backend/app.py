from flask import Flask, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import db_utils # Import the new db_utils module

# Import simulation engine functions
from simulation_engine import traditional_model, causation_model
import numpy # For custom JSON encoder if numpy types are returned by simulation
import json # For parsing complex JSONB fields if necessary, though engines should return dicts

app = Flask(__name__)

# Simulated user data store (in-memory list) - For signup/login
users_db = []
user_id_counter = 1

# Placeholder for database connection details (not used in this simulated version)
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "user": "emds_user",
    "password": "password",
    "database": "emds_db"
}

# --- Custom JSON Encoder for Numpy types ---
class NumpyJSONEncoder(jsonify.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer, np.floating, np.bool_)):
            return obj.item()
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        # Add handling for other non-serializable types if necessary
        try:
            return super(NumpyJSONEncoder, self).default(obj)
        except TypeError:
            return str(obj) # Fallback to string for other complex types

app.json_encoder = NumpyJSONEncoder


# --- User Authentication (Simplified) ---
def get_current_user_id():
    user_id_from_header = request.headers.get('X-User-ID')
    if user_id_from_header:
        try:
            return int(user_id_from_header)
        except ValueError:
            pass
    return 1 # Default test user

# --- Auth Endpoints ---
@app.route('/api/signup', methods=['POST'])
def signup():
    global user_id_counter
    data = request.get_json()
    if not data or not data.get('username') or not data.get('email') or not data.get('password'):
        return jsonify({"error": "Missing required fields"}), 400
    username = data['username']
    email = data['email']
    if any(u['username'] == username for u in users_db) or any(u['email'] == email for u in users_db):
        return jsonify({"error": "Username or email already exists"}), 409

    new_user = {
        "id": user_id_counter, "username": username, "email": email,
        "password_hash": generate_password_hash(data['password'])
    }
    users_db.append(new_user)
    user_id_counter += 1
    print(f"New user signed up: {new_user['username']}, ID: {new_user['id']}")
    return jsonify({"message": "User created successfully", "user_id": new_user["id"]}), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({"error": "Missing required fields"}), 400
    user = next((u for u in users_db if u['username'] == data['username']), None)
    if not user or not check_password_hash(user['password_hash'], data['password']):
        return jsonify({"error": "Invalid username or password"}), 401

    print(f"User logged in: {user['username']}, ID: {user['id']}")
    return jsonify({
        "message": "Login successful", "user_id": user['id'],
        "username": user['username'], "token": f"placeholder_jwt_token_for_user_{user['id']}"
    }), 200

# --- Scenario CRUD Endpoints ---
@app.route('/api/scenarios', methods=['POST'])
def create_scenario():
    user_id = get_current_user_id()
    data = request.get_json()
    if not data or not data.get('name'):
        return jsonify({"error": "Missing required field: name"}), 400
    try:
        # Pass all data from request body to db_utils function
        new_scenario = db_utils.create_scenario_db(user_id=user_id, **data)
        return jsonify(new_scenario), 201
    except Exception as e:
        return jsonify({"error": "Failed to create scenario", "details": str(e)}), 500

@app.route('/api/scenarios', methods=['GET'])
def get_all_scenarios():
    user_id = get_current_user_id()
    scenarios = db_utils.get_scenarios_by_user_id_db(user_id)
    return jsonify(scenarios), 200

@app.route('/api/scenarios/<int:scenario_id>', methods=['GET'])
def get_scenario(scenario_id):
    user_id = get_current_user_id()
    scenario = db_utils.get_scenario_by_id_db(scenario_id, user_id)
    if scenario:
        return jsonify(scenario), 200
    return jsonify({"error": "Scenario not found or access denied"}), 404

@app.route('/api/scenarios/<int:scenario_id>', methods=['PUT'])
def update_scenario(scenario_id):
    user_id = get_current_user_id()
    data = request.get_json()
    if not data: return jsonify({"error": "No data provided"}), 400
    updated_scenario = db_utils.update_scenario_db(scenario_id, user_id, data)
    if updated_scenario:
        return jsonify(updated_scenario), 200
    return jsonify({"error": "Scenario not found or access denied"}), 404

@app.route('/api/scenarios/<int:scenario_id>', methods=['DELETE'])
def delete_scenario(scenario_id):
    user_id = get_current_user_id()
    if db_utils.delete_scenario_db(scenario_id, user_id):
        return '', 204
    return jsonify({"error": "Scenario not found or access denied"}), 404

# --- Simulation Endpoint ---
@app.route('/api/simulations/run', methods=['POST'])
def run_simulation_endpoint():
    user_id = get_current_user_id()
    data = request.get_json()

    if not data or 'scenario_id' not in data or 'framework' not in data:
        return jsonify({"error": "Missing 'scenario_id' or 'framework' in request body"}), 400

    scenario_id = data['scenario_id']
    framework = data['framework'].lower()

    scenario_data_dict = db_utils.get_scenario_by_id_db(scenario_id, user_id)
    if not scenario_data_dict:
        return jsonify({"error": f"Scenario with ID {scenario_id} not found or access denied."}), 404

    engine_results = None
    simulation_status = 'failure' # Default status
    error_message = None

    print(f"Running simulation for scenario ID: {scenario_id}, framework: {framework}, user ID: {user_id}")

    try:
        if framework == 'traditional':
            engine_results = traditional_model.run_traditional_simulation(scenario_data_dict)
        elif framework == 'causation':
            engine_results = causation_model.run_causation_simulation(scenario_data_dict)
        else:
            db_utils.save_simulation_result_db(
                scenario_id=scenario_id, user_id=user_id, framework_type=framework,
                status='failure', error_message=f"Invalid simulation framework '{framework}'.")
            return jsonify({"error": f"Invalid simulation framework '{framework}'. Supported: 'traditional', 'causation'."}), 400

        if isinstance(engine_results, dict) and engine_results.get('status') == 'success':
            simulation_status = 'success'
        elif isinstance(engine_results, dict) and 'error' in engine_results:
            error_message = engine_results.get('details', engine_results['error'])
            simulation_status = 'failure' # Already default, but explicit
        else: # Unexpected result format from engine
            error_message = "Simulation engine returned an unexpected result format."
            simulation_status = 'failure'

    except Exception as e:
        import traceback
        error_message = f"Unhandled exception during simulation: {str(e)}"
        print(f"{error_message}\n{traceback.format_exc()}")
        simulation_status = 'failure'
        # Fall through to save result and then return error to client

    # Prepare data for saving to DB
    summary_res_for_db = {}
    detailed_gen_res_for_db = []
    detailed_load_res_for_db = []
    detailed_line_res_for_db = []
    contingency_summary_for_db = {}
    total_dispatch_cost = None
    total_consumer_payment = None
    total_generator_revenue = None
    total_security_charges = None

    if simulation_status == 'success' and isinstance(engine_results, dict):
        if framework == 'traditional' and engine_results.get('financial_results'):
            trad_fin = engine_results['financial_results']
            summary_res_for_db = trad_fin.get('system_summary', {})
            detailed_gen_res_for_db = trad_fin.get('generator_details', [])
            detailed_load_res_for_db = trad_fin.get('load_details', [])
            detailed_line_res_for_db = trad_fin.get('line_details', [])
            total_dispatch_cost = summary_res_for_db.get('total_dispatch_cost')
            total_consumer_payment = summary_res_for_db.get('total_consumer_payment_for_energy')
            total_generator_revenue = summary_res_for_db.get('total_generator_revenue')
        elif framework == 'causation' and engine_results.get('final_causation_financials'):
            caus_fin = engine_results['final_causation_financials']
            summary_res_for_db = caus_fin.get('system_summary', {})
            detailed_gen_res_for_db = caus_fin.get('generator_details', [])
            trad_fin_base = engine_results.get('traditional_financials_for_base_case', {})
            detailed_load_res_for_db = trad_fin_base.get('load_details', [])
            detailed_line_res_for_db = trad_fin_base.get('line_details', [])
            contingency_summary_for_db = engine_results.get('contingency_analysis_details', {})
            total_dispatch_cost = engine_results.get('base_case_dispatch_solution', {}).get('total_cost')
            total_consumer_payment = summary_res_for_db.get('total_consumer_payment_for_energy')
            total_generator_revenue = summary_res_for_db.get('total_generator_revenue')
            total_security_charges = summary_res_for_db.get('total_security_charges_collected')

    try:
        db_utils.save_simulation_result_db(
            scenario_id=scenario_id, user_id=user_id, framework_type=framework,
            status=simulation_status, error_message=error_message,
            total_dispatch_cost=total_dispatch_cost,
            total_consumer_payment=total_consumer_payment,
            total_generator_revenue=total_generator_revenue,
            total_security_charges_collected=total_security_charges,
            summary_results=summary_res_for_db,
            detailed_generator_results=detailed_gen_res_for_db,
            detailed_load_results=detailed_load_res_for_db,
            detailed_line_results=detailed_line_res_for_db,
            contingency_analysis_summary=contingency_summary_for_db
        )
    except Exception as db_save_exc:
        print(f"CRITICAL: Failed to save simulation result to DB: {db_save_exc}")

    if simulation_status == 'success':
        return jsonify(engine_results), 200
    else:
        return jsonify({"error": f"Simulation failed for framework '{framework}'.", "details": error_message}), 500

# --- Simulation Results Retrieval Endpoints ---
@app.route('/api/scenarios/<int:scenario_id>/results', methods=['GET'])
def get_results_for_scenario(scenario_id):
    user_id = get_current_user_id()
    # First, verify if the user can access the scenario itself
    scenario = db_utils.get_scenario_by_id_db(scenario_id, user_id)
    if not scenario:
        return jsonify({"error": "Scenario not found or access denied"}), 404

    # If scenario access is confirmed, then fetch results for that scenario
    # The db_utils.get_results_by_scenario_id_db also re-checks user_id against scenario ownership,
    # which is redundant here but fine for the simulated DB.
    results_list = db_utils.get_results_by_scenario_id_db(scenario_id, user_id)
    if results_list is None: # Should ideally not happen if scenario was found, implies internal error
        return jsonify({"error": "Failed to retrieve results for scenario"}), 500

    return jsonify(results_list), 200

@app.route('/api/simulations/results/<int:result_id>', methods=['GET'])
def get_simulation_result_by_id(result_id):
    user_id = get_current_user_id()
    # The db_utils.get_result_by_id_db handles checking if the user owns the parent scenario
    result_data = db_utils.get_result_by_id_db(result_id, user_id)
    if result_data:
        return jsonify(result_data), 200
    else:
        return jsonify({"error": "Simulation result not found or access denied"}), 404


if __name__ == '__main__':
    if not any(u['id'] == 1 for u in users_db):
        users_db.append({
            "id": 1, "username": "testuser", "email": "test@example.com",
            "password_hash": generate_password_hash("password")
        })
        print("Added default testuser with ID 1 for scenario and simulation testing.")
    app.run(debug=True, port=5001)
