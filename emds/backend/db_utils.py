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

# --- In-Memory Simulation Results Data Store (Simulation) ---
simulation_results_db = []
next_simulation_result_id = 1


# --- Scenario Helper Functions for Simulated DB Operations ---

def create_scenario_db(user_id, name, description=None, grid_config=None, generator_data=None, load_data=None, transmission_data=None, contingency_data=None, **kwargs):
    """
    Simulates creating a new scenario and storing it in the in-memory list.
    Accepts **kwargs to be robust against extra fields from request.json()
    """
    global next_scenario_id
    now = datetime.utcnow()
    new_scenario = {
        "id": next_scenario_id,
        "user_id": user_id,
        "name": name,
        "description": description or "",
        "grid_config": grid_config or {},
        "generator_data": generator_data or [],
        "load_data": load_data or [],
        "transmission_data": transmission_data or [],
        "contingency_data": contingency_data or {},
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
    s1_data = {"name": "Summer Peak", "description": "A scenario for peak summer load.",
               "grid_config": {"num_buses": 10}, "generator_data": [{"id": "G1"}],
               "load_data": [{"id": "L1"}], "transmission_data": [{"id": "T1"}],
               "contingency_data": {}}
    s1 = create_scenario_db(user_id=test_user_id, **s1_data)

    s2_data = {"name": "Winter Off-Peak", "description": "A scenario for winter off-peak.",
               "grid_config": {"num_buses": 5}, "generator_data": [{"id": "G2"}],
               "load_data": [{"id": "L2"}], "transmission_data": [{"id": "T2"}],
               "contingency_data": {}}
    s2 = create_scenario_db(user_id=test_user_id, **s2_data)

    s3_data = {"name": "User 2 Scenario", "description": "Test scenario for another user.",
               "grid_config": {"num_buses": 3}, "generator_data": [],
               "load_data": [], "transmission_data": [], "contingency_data": {}}
    s3 = create_scenario_db(user_id=test_user_id_2, **s3_data)

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

    print("\n--- Scenario DB Utils Tests Passed (Simulated) ---")


# --- Simulation Results Helper Functions for Simulated DB Operations ---

def save_simulation_result_db(scenario_id, user_id, framework_type, status,
                              summary_results=None, detailed_generator_results=None,
                              detailed_load_results=None, detailed_line_results=None,
                              contingency_analysis_summary=None, error_message=None,
                              total_dispatch_cost=None, total_consumer_payment=None,
                              total_generator_revenue=None, total_security_charges_collected=None,
                              notes=None):
    """
    Simulates saving a simulation result to the in-memory list.
    """
    global next_simulation_result_id
    now = datetime.utcnow()

    new_result = {
        "id": next_simulation_result_id,
        "scenario_id": scenario_id,
        "user_id": user_id,
        "framework_type": framework_type,
        "simulation_timestamp": now.isoformat(),
        "status": status, # 'success', 'failure'
        "error_message": error_message,

        "total_dispatch_cost": total_dispatch_cost,
        "total_consumer_payment": total_consumer_payment,
        "total_generator_revenue": total_generator_revenue,
        "total_security_charges_collected": total_security_charges_collected,

        "summary_results": summary_results or {},
        "detailed_generator_results": detailed_generator_results or [],
        "detailed_load_results": detailed_load_results or [],
        "detailed_line_results": detailed_line_results or [],
        "contingency_analysis_summary": contingency_analysis_summary or {},
        "notes": notes
    }
    simulation_results_db.append(new_result)
    next_simulation_result_id += 1
    print(f"Simulation result saved: ID {new_result['id']} for scenario ID {scenario_id}, Status: {status}")
    return copy.deepcopy(new_result)

def get_results_by_scenario_id_db(scenario_id, user_id):
    """
    Simulates retrieving all simulation results for a given scenario_id,
    ensuring the user has access (owns the scenario or the result directly).
    """
    # First, check if user owns the scenario associated with these results
    scenario = get_scenario_by_id_db(scenario_id, user_id)
    if not scenario: # User does not own the scenario
        # Or, if results can be public/shared later, this logic might change
        return []

    results = [copy.deepcopy(r) for r in simulation_results_db if r["scenario_id"] == scenario_id]
    return results

def get_result_by_id_db(result_id, user_id):
    """
    Simulates retrieving a specific simulation result by its ID,
    ensuring the user has access.
    """
    for result in simulation_results_db:
        if result["id"] == result_id:
            # Check if user owns the scenario linked to this result
            scenario = get_scenario_by_id_db(result["scenario_id"], user_id)
            if scenario: # User owns the scenario, so can see the result
                return copy.deepcopy(result)
            # Add more complex sharing logic here if needed in future
            break
    return None


if __name__ == '__main__':
    # (Existing scenario tests will run first)

    print("\n\n--- Testing Simulation Results DB Utils ---")
    if not scenarios_db: # Ensure there's a scenario to link to
        print("No scenarios found from previous tests. Skipping sim results tests.")
    else:
        test_scenario_id_for_results = scenarios_db[0]['id'] # Use s1
        test_user_id_for_results = scenarios_db[0]['user_id'] # User who owns s1

        # Save a successful result
        res1_summary = {"total_cost": 5000, "avg_lmp": 25.5}
        res1_gen_details = [{"id": "G1", "power": 50, "profit": 100}]
        res1 = save_simulation_result_db(
            scenario_id=test_scenario_id_for_results,
            user_id=test_user_id_for_results,
            framework_type="traditional",
            status="success",
            summary_results=res1_summary,
            detailed_generator_results=res1_gen_details,
            total_dispatch_cost=5000
        )
        assert res1 is not None
        assert res1["status"] == "success"
        assert res1["summary_results"]["total_cost"] == 5000

        # Save a failure result
        res2 = save_simulation_result_db(
            scenario_id=test_scenario_id_for_results,
            user_id=test_user_id_for_results,
            framework_type="causation",
            status="failure",
            error_message="Contingency analysis failed: Division by zero."
        )
        assert res2 is not None
        assert res2["status"] == "failure"
        assert "Division by zero" in res2["error_message"]

        # Get results by scenario
        scenario_res = get_results_by_scenario_id_db(test_scenario_id_for_results, test_user_id_for_results)
        print(f"\nResults for scenario {test_scenario_id_for_results}: {scenario_res}")
        assert len(scenario_res) == 2

        # Attempt to get results for a scenario the user doesn't own (if another user existed and had scenarios)
        # For now, this is hard to test without creating a result for a scenario owned by user_id_2
        # and trying to fetch with test_user_id_1.
        # Let's assume user_id_2 (if they have scenarios) cannot see test_user_id_1's results via this function.
        if len(scenarios_db) > 2 and scenarios_db[2]['user_id'] != test_user_id_for_results : # If s3 exists and owned by user_id_2
             other_user_id = scenarios_db[2]['user_id']
             other_scenario_id = scenarios_db[2]['id']
             save_simulation_result_db(other_scenario_id, other_user_id, "traditional", "success")

             foreign_results = get_results_by_scenario_id_db(other_scenario_id, test_user_id_for_results) # user 1 tries to get user 2's results
             assert len(foreign_results) == 0, "User should not see results for scenarios they don't own"
             print(f"\nUser {test_user_id_for_results} correctly sees no results for scenario {other_scenario_id} they don't own.")


        # Get result by ID
        retrieved_res1 = get_result_by_id_db(res1["id"], test_user_id_for_results)
        print(f"\nRetrieved result by ID {res1['id']}: {retrieved_res1}")
        assert retrieved_res1 is not None
        assert retrieved_res1["framework_type"] == "traditional"

        # Attempt to get result ID that user doesn't own (scenario link)
        # This requires a bit more setup: result for a scenario owned by another user.
        if 'other_user_id' in locals() and 'other_scenario_id' in locals():
            # Find the result ID for the other user's scenario
            other_users_results_list = [r for r in simulation_results_db if r['scenario_id'] == other_scenario_id]
            if other_users_results_list:
                other_res_id = other_users_results_list[0]['id']
                foreign_res_by_id = get_result_by_id_db(other_res_id, test_user_id_for_results) # User 1 tries to get user 2's result
                assert foreign_res_by_id is None, "User should not get specific result for scenario they don't own"
                print(f"\nUser {test_user_id_for_results} correctly cannot retrieve result ID {other_res_id} they don't own.")


        print("\n--- Simulation Results DB Utils Tests Passed (Simulated) ---")
