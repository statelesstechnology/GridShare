import unittest
import copy
from datetime import datetime

# Adjust import path based on actual structure.
# If tests are run from emds/backend/, then:
from db_utils import (
    scenarios_db, next_scenario_id,
    simulation_results_db, next_simulation_result_id,
    create_scenario_db, get_scenario_by_id_db, get_scenarios_by_user_id_db,
    update_scenario_db, delete_scenario_db,
    save_simulation_result_db, get_results_by_scenario_id_db, get_result_by_id_db
)
# Note: User DB functions (create_user_db etc.) were part of app.py's in-memory store,
# not db_utils.py. If they need to be tested here, db_utils would need to own them.
# For now, focusing on what's in db_utils.

class TestDBUtils(unittest.TestCase):

    def setUp(self):
        """Clear in-memory stores before each test."""
        global scenarios_db, next_scenario_id
        global simulation_results_db, next_simulation_result_id

        scenarios_db.clear()
        next_scenario_id = 1
        simulation_results_db.clear()
        next_simulation_result_id = 1

        # Sample users (assuming they would be created elsewhere, like in app.py setup for tests)
        # For db_utils, we mostly care about user_id.
        self.user1_id = 1
        self.user2_id = 2

    def _create_sample_scenario(self, user_id, name_suffix=""):
        return create_scenario_db(
            user_id=user_id,
            name=f"Test Scenario {name_suffix}",
            description="A test description",
            grid_config={"num_buses": 2},
            generator_data=[{"id": "G1", "bus_id": 1, "capacity_mw": 100, "cost_energy_mwh": 20}],
            load_data=[{"id": "L1", "bus_id": 2, "demand_mw": 70}],
            transmission_data=[{"id": "T1", "from_bus_id": 1, "to_bus_id": 2, "flow_limit_mw": 50}],
            contingency_data={}
        )

    def test_create_scenario_db(self):
        scenario = self._create_sample_scenario(self.user1_id, "Create Test")
        self.assertEqual(scenario['name'], "Test Scenario Create Test")
        self.assertEqual(scenario['user_id'], self.user1_id)
        self.assertEqual(scenario['id'], 1)
        self.assertEqual(len(scenarios_db), 1)
        self.assertEqual(scenarios_db[0]['name'], "Test Scenario Create Test")

    def test_get_scenario_by_id_db(self):
        s1 = self._create_sample_scenario(self.user1_id, "S1")
        s2 = self._create_sample_scenario(self.user2_id, "S2")

        retrieved_s1 = get_scenario_by_id_db(s1['id'], self.user1_id)
        self.assertIsNotNone(retrieved_s1)
        self.assertEqual(retrieved_s1['name'], "Test Scenario S1")

        # Test access denied for wrong user
        retrieved_s1_wrong_user = get_scenario_by_id_db(s1['id'], self.user2_id)
        self.assertIsNone(retrieved_s1_wrong_user)

        # Test non-existent ID
        retrieved_non_existent = get_scenario_by_id_db(999, self.user1_id)
        self.assertIsNone(retrieved_non_existent)

    def test_get_scenarios_by_user_id_db(self):
        self._create_sample_scenario(self.user1_id, "U1S1")
        self._create_sample_scenario(self.user1_id, "U1S2")
        self._create_sample_scenario(self.user2_id, "U2S1")

        user1_scenarios = get_scenarios_by_user_id_db(self.user1_id)
        self.assertEqual(len(user1_scenarios), 2)
        self.assertTrue(any(s['name'] == "Test Scenario U1S1" for s in user1_scenarios))
        self.assertTrue(any(s['name'] == "Test Scenario U1S2" for s in user1_scenarios))

        user2_scenarios = get_scenarios_by_user_id_db(self.user2_id)
        self.assertEqual(len(user2_scenarios), 1)
        self.assertEqual(user2_scenarios[0]['name'], "Test Scenario U2S1")

        no_scenarios_user = get_scenarios_by_user_id_db(3) # Non-existent user
        self.assertEqual(len(no_scenarios_user), 0)

    def test_update_scenario_db(self):
        scenario = self._create_sample_scenario(self.user1_id, "Update Original")
        original_id = scenario['id']
        update_data = {"name": "Updated Name", "description": "Updated Description"}

        updated = update_scenario_db(original_id, self.user1_id, update_data)
        self.assertIsNotNone(updated)
        self.assertEqual(updated['name'], "Updated Name")
        self.assertEqual(updated['description'], "Updated Description")
        self.assertNotEqual(updated['updated_at'], scenario['updated_at'])

        # Test cannot update other user's scenario
        cannot_update = update_scenario_db(original_id, self.user2_id, update_data)
        self.assertIsNone(cannot_update)

        # Check original data is still there after failed update attempt
        retrieved_original = get_scenario_by_id_db(original_id, self.user1_id)
        self.assertEqual(retrieved_original['name'], "Updated Name") # Should be the updated name by user1

    def test_delete_scenario_db(self):
        s1 = self._create_sample_scenario(self.user1_id, "ToDelete1")
        s2 = self._create_sample_scenario(self.user1_id, "Keep1")
        s3 = self._create_sample_scenario(self.user2_id, "ToDeleteByUser2")

        self.assertTrue(delete_scenario_db(s1['id'], self.user1_id))
        self.assertIsNone(get_scenario_by_id_db(s1['id'], self.user1_id))
        self.assertEqual(len(get_scenarios_by_user_id_db(self.user1_id)), 1) # s2 should remain

        # Test cannot delete other user's scenario
        self.assertFalse(delete_scenario_db(s3['id'], self.user1_id))
        self.assertIsNotNone(get_scenario_by_id_db(s3['id'], self.user2_id)) # s3 still there for user 2

        # Test delete non-existent
        self.assertFalse(delete_scenario_db(999, self.user1_id))

    def test_save_simulation_result_db(self):
        scenario = self._create_sample_scenario(self.user1_id, "ForSimResult")
        result = save_simulation_result_db(
            scenario_id=scenario['id'],
            user_id=self.user1_id, # User who owns the scenario
            framework_type="traditional",
            status="success",
            summary_results={"cost": 1000},
            detailed_generator_results=[{"id": "G1", "power": 50}]
        )
        self.assertEqual(result['id'], 1)
        self.assertEqual(result['scenario_id'], scenario['id'])
        self.assertEqual(result['user_id'], self.user1_id)
        self.assertEqual(result['framework_type'], "traditional")
        self.assertEqual(result['summary_results']['cost'], 1000)
        self.assertEqual(len(simulation_results_db), 1)

    def test_get_results_by_scenario_id_db(self):
        s1 = self._create_sample_scenario(self.user1_id, "S1_Res")
        s2 = self._create_sample_scenario(self.user2_id, "S2_Res") # User 2 scenario

        save_simulation_result_db(s1['id'], self.user1_id, "traditional", "success", {"cost": 1})
        save_simulation_result_db(s1['id'], self.user1_id, "causation", "failure", error_message="error1")
        save_simulation_result_db(s2['id'], self.user2_id, "traditional", "success", {"cost": 2})

        user1_s1_results = get_results_by_scenario_id_db(s1['id'], self.user1_id)
        self.assertEqual(len(user1_s1_results), 2)

        # User 1 tries to get results for User 2's scenario S2
        user1_s2_results = get_results_by_scenario_id_db(s2['id'], self.user1_id)
        self.assertEqual(len(user1_s2_results), 0, "User 1 should not get results for User 2's scenario S2")

        user2_s2_results = get_results_by_scenario_id_db(s2['id'], self.user2_id)
        self.assertEqual(len(user2_s2_results), 1)
        self.assertEqual(user2_s2_results[0]['summary_results']['cost'], 2)

    def test_get_result_by_id_db(self):
        s1 = self._create_sample_scenario(self.user1_id, "S1_SingleRes")
        s2 = self._create_sample_scenario(self.user2_id, "S2_SingleRes")

        res1 = save_simulation_result_db(s1['id'], self.user1_id, "traditional", "success", {"cost": 100})
        res2_user2 = save_simulation_result_db(s2['id'], self.user2_id, "causation", "success", {"cost": 200})

        retrieved_res1 = get_result_by_id_db(res1['id'], self.user1_id)
        self.assertIsNotNone(retrieved_res1)
        self.assertEqual(retrieved_res1['summary_results']['cost'], 100)

        # User 1 tries to get User 2's result
        retrieved_res2_user1 = get_result_by_id_db(res2_user2['id'], self.user1_id)
        self.assertIsNone(retrieved_res2_user1, "User 1 should not access User 2's result by ID")

        retrieved_res2_user2 = get_result_by_id_db(res2_user2['id'], self.user2_id)
        self.assertIsNotNone(retrieved_res2_user2)
        self.assertEqual(retrieved_res2_user2['summary_results']['cost'], 200)

        # Non-existent result ID
        non_existent = get_result_by_id_db(999, self.user1_id)
        self.assertIsNone(non_existent)

if __name__ == '__main__':
    unittest.main()
