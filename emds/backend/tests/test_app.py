import unittest
import json
from unittest.mock import patch, MagicMock

# Assuming app.py and db_utils.py are in the parent directory relative to tests/
# This might need adjustment based on how tests are run (e.g. from backend/ or emds/)
import sys
import os
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app # Flask app instance
from db_utils import (
    scenarios_db, next_scenario_id,
    simulation_results_db, next_simulation_result_id,
    users_db as app_users_db, user_id_counter as app_user_id_counter # If testing signup/login that uses app's user store
)


class TestApp(unittest.TestCase):

    def setUp(self):
        app.testing = True
        self.client = app.test_client()

        # Clear in-memory stores before each test
        # For db_utils stores
        scenarios_db.clear()
        setattr(sys.modules['db_utils'], 'next_scenario_id', 1) # Reset counter

        simulation_results_db.clear()
        setattr(sys.modules['db_utils'], 'next_simulation_result_id', 1) # Reset counter

        # For app.py's own user store (if used by signup/login directly)
        app_users_db.clear()
        setattr(sys.modules['app'], 'user_id_counter', 1) # Reset counter in app.py

        # Create a default test user directly in the app's user store for authenticated endpoints
        # This bypasses signup/login for many tests, focusing on endpoint logic.
        # Alternatively, call signup/login in setUp or individual tests.
        self.test_user_id = 1
        app_users_db.append({
            "id": self.test_user_id, "username": "testuser", "email": "test@example.com",
            "password_hash": app.generate_password_hash("password") # Use app's hash function
        })
        setattr(sys.modules['app'], 'user_id_counter', self.test_user_id + 1)


        self.default_headers = {'X-User-ID': str(self.test_user_id)}


    def test_signup_and_login(self):
        # Signup
        signup_data = {"username": "newuser", "email": "new@example.com", "password": "newpassword"}
        response = self.client.post('/api/signup', json=signup_data)
        self.assertEqual(response.status_code, 201)
        json_data = response.get_json()
        self.assertIn("user_id", json_data)
        new_user_id = json_data["user_id"]

        # Login with new user
        login_data = {"username": "newuser", "password": "newpassword"}
        response = self.client.post('/api/login', json=login_data)
        self.assertEqual(response.status_code, 200)
        json_data = response.get_json()
        self.assertEqual(json_data["user_id"], new_user_id)
        self.assertEqual(json_data["username"], "newuser")

        # Test existing user signup
        response = self.client.post('/api/signup', json=signup_data)
        self.assertEqual(response.status_code, 409) # Conflict

    def test_create_scenario_endpoint(self):
        scenario_data = {
            "name": "API Test Scenario", "description": "Desc",
            "grid_config": {"num_buses": 1},
            "generator_data": [{"id": "G1", "bus_id": 1, "capacity_mw": 10, "cost_energy_mwh":10}],
        }
        response = self.client.post('/api/scenarios', json=scenario_data, headers=self.default_headers)
        self.assertEqual(response.status_code, 201)
        json_data = response.get_json()
        self.assertEqual(json_data['name'], "API Test Scenario")
        self.assertEqual(json_data['user_id'], self.test_user_id)
        self.assertTrue(len(scenarios_db) == 1) # Check db_utils store

    def test_get_all_scenarios_endpoint(self):
        # Create a scenario for the test user
        self.client.post('/api/scenarios', json={"name": "S1"}, headers=self.default_headers)
        self.client.post('/api/scenarios', json={"name": "S2"}, headers=self.default_headers)

        response = self.client.get('/api/scenarios', headers=self.default_headers)
        self.assertEqual(response.status_code, 200)
        json_data = response.get_json()
        self.assertEqual(len(json_data), 2)

    def test_get_single_scenario_endpoint(self):
        post_response = self.client.post('/api/scenarios', json={"name": "S_Single"}, headers=self.default_headers)
        scenario_id = post_response.get_json()['id']

        response = self.client.get(f'/api/scenarios/{scenario_id}', headers=self.default_headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['name'], "S_Single")

        # Test not found
        response = self.client.get('/api/scenarios/999', headers=self.default_headers)
        self.assertEqual(response.status_code, 404)

        # Test access by another user (create scenario with user 1, try to get with user 2 header)
        other_user_headers = {'X-User-ID': str(self.test_user_id + 10)} # Non-existent or other user
        response_other_user = self.client.get(f'/api/scenarios/{scenario_id}', headers=other_user_headers)
        self.assertEqual(response_other_user.status_code, 404) # Should be 404 as scenario not found for this user context

    def test_update_scenario_endpoint(self):
        post_response = self.client.post('/api/scenarios', json={"name": "S_Update"}, headers=self.default_headers)
        scenario_id = post_response.get_json()['id']

        update_data = {"name": "Updated S_Update", "description": "Now updated."}
        response = self.client.put(f'/api/scenarios/{scenario_id}', json=update_data, headers=self.default_headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['name'], "Updated S_Update")

    def test_delete_scenario_endpoint(self):
        post_response = self.client.post('/api/scenarios', json={"name": "S_Delete"}, headers=self.default_headers)
        scenario_id = post_response.get_json()['id']

        response = self.client.delete(f'/api/scenarios/{scenario_id}', headers=self.default_headers)
        self.assertEqual(response.status_code, 204) # No content

        get_response = self.client.get(f'/api/scenarios/{scenario_id}', headers=self.default_headers)
        self.assertEqual(get_response.status_code, 404) # Should be gone


    @patch('app.traditional_model.run_traditional_simulation')
    @patch('app.causation_model.run_causation_simulation')
    @patch('app.db_utils.save_simulation_result_db') # Mock the save function
    def test_run_simulation_endpoint(self, mock_save_result, mock_run_causation, mock_run_traditional):
        # Setup: Create a scenario first
        scenario_data = {"name": "SimScenario", "grid_config": {"num_buses": 1}}
        post_response = self.client.post('/api/scenarios', json=scenario_data, headers=self.default_headers)
        self.assertEqual(post_response.status_code, 201)
        scenario_id = post_response.get_json()['id']

        # Mock simulation engine responses
        mock_run_traditional.return_value = {"status": "success", "total_cost": 100, "details": "Trad sim complete"}
        mock_run_causation.return_value = {"status": "success", "total_cost": 120, "security_charges": 20, "details": "Caus sim complete"}
        mock_save_result.return_value = {"id": 1, "message": "Result saved"} # Mock DB save response

        # Test traditional framework
        sim_payload_trad = {"scenario_id": scenario_id, "framework": "traditional"}
        response_trad = self.client.post('/api/simulations/run', json=sim_payload_trad, headers=self.default_headers)
        self.assertEqual(response_trad.status_code, 200)
        json_trad = response_trad.get_json()
        self.assertEqual(json_trad["details"], "Trad sim complete")
        mock_run_traditional.assert_called_once()
        mock_save_result.assert_called() # Check that save was called
        # More specific check for save_simulation_result_db arguments
        last_call_args_trad = mock_save_result.call_args.kwargs
        self.assertEqual(last_call_args_trad['scenario_id'], scenario_id)
        self.assertEqual(last_call_args_trad['framework_type'], "traditional")
        self.assertEqual(last_call_args_trad['status'], "success")


        # Test causation framework
        sim_payload_caus = {"scenario_id": scenario_id, "framework": "causation"}
        response_caus = self.client.post('/api/simulations/run', json=sim_payload_caus, headers=self.default_headers)
        self.assertEqual(response_caus.status_code, 200)
        json_caus = response_caus.get_json()
        self.assertEqual(json_caus["details"], "Caus sim complete")
        mock_run_causation.assert_called_once()
        last_call_args_caus = mock_save_result.call_args.kwargs
        self.assertEqual(last_call_args_caus['framework_type'], "causation")

        # Test invalid framework
        sim_payload_invalid = {"scenario_id": scenario_id, "framework": "unknown"}
        response_invalid = self.client.post('/api/simulations/run', json=sim_payload_invalid, headers=self.default_headers)
        self.assertEqual(response_invalid.status_code, 400)

        # Test scenario not found
        sim_payload_no_scenario = {"scenario_id": 999, "framework": "traditional"}
        response_no_scenario = self.client.post('/api/simulations/run', json=sim_payload_no_scenario, headers=self.default_headers)
        self.assertEqual(response_no_scenario.status_code, 404)

        # Test simulation engine failure
        mock_run_traditional.reset_mock() # Reset call count for next test
        mock_run_traditional.return_value = {"status": "failure", "error": "Engine exploded"}
        response_trad_fail = self.client.post('/api/simulations/run', json=sim_payload_trad, headers=self.default_headers)
        self.assertEqual(response_trad_fail.status_code, 500) # API indicates server error
        json_trad_fail = response_trad_fail.get_json()
        self.assertIn("Simulation failed", json_trad_fail['error'])
        self.assertEqual(json_trad_fail['details'], "Engine exploded")
        last_call_args_fail = mock_save_result.call_args.kwargs
        self.assertEqual(last_call_args_fail['status'], "failure")
        self.assertEqual(last_call_args_fail['error_message'], "Engine exploded")


    @patch('app.db_utils.get_results_by_scenario_id_db')
    def test_get_results_for_scenario_endpoint(self, mock_get_results):
        # Need a scenario to exist for the first check in the endpoint
        scenario_data = {"name": "ResultsScenario"}
        post_response = self.client.post('/api/scenarios', json=scenario_data, headers=self.default_headers)
        scenario_id = post_response.get_json()['id']

        mock_get_results.return_value = [{"id": 1, "framework_type": "traditional", "status": "success"}]
        response = self.client.get(f'/api/scenarios/{scenario_id}/results', headers=self.default_headers)
        self.assertEqual(response.status_code, 200)
        json_data = response.get_json()
        self.assertEqual(len(json_data), 1)
        self.assertEqual(json_data[0]['framework_type'], "traditional")
        mock_get_results.assert_called_with(scenario_id, self.test_user_id)

        # Test scenario not found (or user does not own it)
        response_not_found = self.client.get('/api/scenarios/999/results', headers=self.default_headers)
        self.assertEqual(response_not_found.status_code, 404)


    @patch('app.db_utils.get_result_by_id_db')
    def test_get_simulation_result_by_id_endpoint(self, mock_get_result):
        mock_get_result.return_value = {"id": 1, "framework_type": "causation", "status": "failure", "error_message":"Test error"}
        response = self.client.get('/api/simulations/results/1', headers=self.default_headers)
        self.assertEqual(response.status_code, 200)
        json_data = response.get_json()
        self.assertEqual(json_data['id'], 1)
        self.assertEqual(json_data['framework_type'], "causation")
        mock_get_result.assert_called_with(1, self.test_user_id)

        # Test result not found (or user not authorized)
        mock_get_result.return_value = None
        response_not_found = self.client.get('/api/simulations/results/999', headers=self.default_headers)
        self.assertEqual(response_not_found.status_code, 404)


if __name__ == '__main__':
    unittest.main()
