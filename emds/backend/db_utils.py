import copy
from datetime import datetime

# --- Database Connection (Placeholder) ---
def get_db_connection():
    """
    Placeholder for establishing a database connection.
    In a real application, this would connect to PostgreSQL.
    """
    print("Attempting to connect to the database (simulated)...")
    # Example: return psycopg2.connect(host="...", database="...", user="...", password="...")
    return None

# --- In-Memory Scenario Data Store (Simulation) ---
scenarios_db = []
next_scenario_id = 1

# --- Helper Functions for Simulated DB Operations ---

def create_scenario_db(user_id, name, description, grid_config, generator_data, load_data, transmission_data, contingency_data):
    """
    Simulates creating a new scenario and storing it in the in-memory list.
    """
    global next_scenario_id
    now = datetime.utcnow()
    new_scenario = {
        "id": next_scenario_id,
        "user_id": user_id,
        "name": name,
        "description": description,
        "grid_config": grid_config,
        "generator_data": generator_data,
        "load_data": load_data,
        "transmission_data": transmission_data,
        "contingency_data": contingency_data,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    scenarios_db.append(new_scenario)
    next_scenario_id += 1
    return copy.deepcopy(new_scenario)

def get_scenario_by_id_db(scenario_id, user_id):
    """
    Simulates retrieving a scenario by its ID, ensuring it belongs to the user.
    """
    for scenario in scenarios_db:
        if scenario["id"] == scenario_id and scenario["user_id"] == user_id:
            return copy.deepcopy(scenario)
    return None

def get_scenarios_by_user_id_db(user_id):
    """
    Simulates retrieving all scenarios for a given user_id.
    """
    user_scenarios = [copy.deepcopy(s) for s in scenarios_db if s["user_id"] == user_id]
    return user_scenarios

def update_scenario_db(scenario_id, user_id, data_to_update):
    """
    Simulates updating an existing scenario.
    Only updates fields present in data_to_update.
    """
    for i, scenario in enumerate(scenarios_db):
        if scenario["id"] == scenario_id and scenario["user_id"] == user_id:
            updated_scenario = scenario.copy() # Work on a copy
            for key, value in data_to_update.items():
                if key not in ["id", "user_id", "created_at", "updated_at"]: # These should not be updated directly
                    updated_scenario[key] = value
            updated_scenario["updated_at"] = datetime.utcnow().isoformat()
            scenarios_db[i] = updated_scenario # Replace original with updated
            return copy.deepcopy(updated_scenario)
    return None # Scenario not found or user mismatch

def delete_scenario_db(scenario_id, user_id):
    """
    Simulates deleting a scenario.
    Returns True if deletion was successful, False otherwise.
    """
    global scenarios_db
    initial_len = len(scenarios_db)
    # Filter out the scenario to be deleted
    scenarios_db = [s for s in scenarios_db if not (s["id"] == scenario_id and s["user_id"] == user_id)]
    return len(scenarios_db) < initial_len

# Example usage (for testing this file directly)
if __name__ == '__main__':
    # Simulate some users from app.py (users_db)
    # This is just for standalone testing of db_utils.py
    # In the real app, user_id will come from the authenticated session.
    test_user_id = 1
    test_user_id_2 = 2

    print("--- Testing Scenario DB Utils ---")

    # Create scenarios
    s1 = create_scenario_db(test_user_id, "Summer Peak", "A scenario for peak summer load.",
                            {"num_buses": 10}, [{"id": "G1"}], [{"id": "L1"}], [{"id": "T1"}], {})
    s2 = create_scenario_db(test_user_id, "Winter Off-Peak", "A scenario for winter off-peak.",
                            {"num_buses": 5}, [{"id": "G2"}], [{"id": "L2"}], [{"id": "T2"}], {})
    s3 = create_scenario_db(test_user_id_2, "User 2 Scenario", "Test scenario for another user.",
                            {"num_buses": 3}, [], [], [], {})

    print(f"\nInitial scenarios_db: {scenarios_db}")

    # Get scenarios by user
    user1_scenarios = get_scenarios_by_user_id_db(test_user_id)
    print(f"\nScenarios for user {test_user_id}: {user1_scenarios}")
    assert len(user1_scenarios) == 2

    user2_scenarios = get_scenarios_by_user_id_db(test_user_id_2)
    print(f"\nScenarios for user {test_user_id_2}: {user2_scenarios}")
    assert len(user2_scenarios) == 1

    # Get scenario by ID
    retrieved_s1 = get_scenario_by_id_db(s1["id"], test_user_id)
    print(f"\nRetrieved scenario {s1['id']} for user {test_user_id}: {retrieved_s1}")
    assert retrieved_s1 is not None

    # Attempt to get scenario belonging to another user
    retrieved_s3_wrong_user = get_scenario_by_id_db(s3["id"], test_user_id)
    print(f"\nAttempt to retrieve scenario {s3['id']} for wrong user {test_user_id}: {retrieved_s3_wrong_user}")
    assert retrieved_s3_wrong_user is None

    # Update scenario
    update_data = {"name": "Summer Peak Load (Updated)", "description": "Updated description."}
    updated_s1 = update_scenario_db(s1["id"], test_user_id, update_data)
    print(f"\nUpdated scenario {s1['id']}: {updated_s1}")
    assert updated_s1["name"] == "Summer Peak Load (Updated)"
    assert updated_s1["updated_at"] != s1["updated_at"]

    # Attempt to update non-existent scenario
    non_existent_update = update_scenario_db(999, test_user_id, {"name": "Does not exist"})
    print(f"\nAttempt to update non-existent scenario: {non_existent_update}")
    assert non_existent_update is None

    # Delete scenario
    delete_success = delete_scenario_db(s2["id"], test_user_id)
    print(f"\nDeletion of scenario {s2['id']} successful: {delete_success}")
    assert delete_success
    assert get_scenario_by_id_db(s2["id"], test_user_id) is None
    assert len(get_scenarios_by_user_id_db(test_user_id)) == 1

    # Attempt to delete already deleted scenario
    delete_failure = delete_scenario_db(s2["id"], test_user_id)
    print(f"\nAttempt to delete already deleted scenario {s2['id']} successful: {delete_failure}")
    assert not delete_failure

    print("\n--- DB Utils Tests Passed (Simulated) ---")
