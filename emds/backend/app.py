from flask import Flask, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import db_utils # Import the new db_utils module

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

# --- User Authentication (Simplified) ---
def get_current_user_id():
    """
    Placeholder for getting the current user's ID.
    In a real app, this would come from a decoded JWT token or session.
    For now, we can try to get it from a header or default to a test user.
    """
    # Attempt to get user_id from a custom header (e.g., X-User-ID)
    # This is a temporary measure for simulation without real auth.
    user_id_from_header = request.headers.get('X-User-ID')
    if user_id_from_header:
        try:
            return int(user_id_from_header)
        except ValueError:
            pass # Fallback if header is not a valid integer
    return 1 # Default to user_id 1 if no header is present or valid


# --- Auth Endpoints ---
@app.route('/api/signup', methods=['POST'])
def signup():
    global user_id_counter
    data = request.get_json()

    if not data or not data.get('username') or not data.get('email') or not data.get('password'):
        return jsonify({"error": "Missing required fields (username, email, password)"}), 400

    username = data['username']
    email = data['email']
    password = data['password']

    if any(user['username'] == username for user in users_db):
        return jsonify({"error": "Username already exists"}), 409
    if any(user['email'] == email for user in users_db):
        return jsonify({"error": "Email already exists"}), 409

    password_hash = generate_password_hash(password)
    new_user = {
        "id": user_id_counter,
        "username": username,
        "email": email,
        "password_hash": password_hash,
        # "created_at": datetime.utcnow().isoformat() # Assuming this is handled by DB schema
    }
    users_db.append(new_user)
    user_id_counter += 1
    # In a real app, you'd also save this to the 'users' table in PostgreSQL.
    print(f"New user signed up: {new_user}")
    return jsonify({"message": "User created successfully", "user_id": new_user["id"]}), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({"error": "Missing required fields (username, password)"}), 400

    username = data['username']
    password = data['password']
    user = next((user for user in users_db if user['username'] == username), None)

    if not user:
        return jsonify({"error": "User not found"}), 404

    if check_password_hash(user['password_hash'], password):
        # Return user_id in login response so client can use it in X-User-ID header for subsequent requests
        return jsonify({
            "message": "Login successful",
            "user_id": user['id'],
            "username": user['username'],
            "token": f"placeholder_jwt_token_for_user_{user['id']}" # Simulate a token
        }), 200
    else:
        return jsonify({"error": "Incorrect password"}), 401

# --- Scenario CRUD Endpoints ---

@app.route('/api/scenarios', methods=['POST'])
def create_scenario():
    user_id = get_current_user_id() # Authenticate/identify user
    data = request.get_json()

    if not data or not data.get('name'):
        return jsonify({"error": "Missing required field: name"}), 400

    # Extract data, providing defaults for optional fields
    name = data['name']
    description = data.get('description', "") # Optional
    grid_config = data.get('grid_config', {})
    generator_data = data.get('generator_data', [])
    load_data = data.get('load_data', [])
    transmission_data = data.get('transmission_data', [])
    contingency_data = data.get('contingency_data', {})

    try:
        new_scenario = db_utils.create_scenario_db(
            user_id=user_id,
            name=name,
            description=description,
            grid_config=grid_config,
            generator_data=generator_data,
            load_data=load_data,
            transmission_data=transmission_data,
            contingency_data=contingency_data
        )
        return jsonify(new_scenario), 201
    except Exception as e:
        # Log the exception e
        return jsonify({"error": "Failed to create scenario", "details": str(e)}), 500

@app.route('/api/scenarios', methods=['GET'])
def get_all_scenarios():
    user_id = get_current_user_id()
    try:
        scenarios = db_utils.get_scenarios_by_user_id_db(user_id)
        return jsonify(scenarios), 200
    except Exception as e:
        return jsonify({"error": "Failed to retrieve scenarios", "details": str(e)}), 500

@app.route('/api/scenarios/<int:scenario_id>', methods=['GET'])
def get_scenario(scenario_id):
    user_id = get_current_user_id()
    try:
        scenario = db_utils.get_scenario_by_id_db(scenario_id, user_id)
        if scenario:
            return jsonify(scenario), 200
        else:
            return jsonify({"error": "Scenario not found or access denied"}), 404
    except Exception as e:
        return jsonify({"error": "Failed to retrieve scenario", "details": str(e)}), 500

@app.route('/api/scenarios/<int:scenario_id>', methods=['PUT'])
def update_scenario(scenario_id):
    user_id = get_current_user_id()
    data_to_update = request.get_json()

    if not data_to_update:
        return jsonify({"error": "No data provided for update"}), 400

    try:
        updated_scenario = db_utils.update_scenario_db(scenario_id, user_id, data_to_update)
        if updated_scenario:
            return jsonify(updated_scenario), 200
        else:
            # This could be due to not found, or user_id mismatch (handled in db_utils)
            return jsonify({"error": "Scenario not found or access denied"}), 404
    except Exception as e:
        return jsonify({"error": "Failed to update scenario", "details": str(e)}), 500

@app.route('/api/scenarios/<int:scenario_id>', methods=['DELETE'])
def delete_scenario(scenario_id):
    user_id = get_current_user_id()
    try:
        deleted = db_utils.delete_scenario_db(scenario_id, user_id)
        if deleted:
            return '', 204  # No Content
        else:
            # This could be due to not found, or user_id mismatch (handled in db_utils)
            return jsonify({"error": "Scenario not found or access denied"}), 404
    except Exception as e:
        return jsonify({"error": "Failed to delete scenario", "details": str(e)}), 500

if __name__ == '__main__':
    # This is for development purposes only.
    # In production, use a WSGI server like Gunicorn.
    # Example: Create a dummy user for testing scenario endpoints if not using signup/login
    if not any(u['id'] == 1 for u in users_db): # Add a default user if not present
        users_db.append({
            "id": 1, "username": "testuser", "email": "test@example.com",
            "password_hash": generate_password_hash("password")
        })
        print("Added default testuser with ID 1 for scenario testing.")

    app.run(debug=True, port=5001)
