import unittest
import numpy as np
from unittest.mock import patch, MagicMock

# Assuming simulation_engine is in the parent directory relative to tests/
# This might need adjustment based on how tests are run
# from simulation_engine import traditional_model, causation_model
import sys
import os
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from simulation_engine import traditional_model, causation_model


class TestSimulationModels(unittest.TestCase):

    def setUp(self):
        self.sample_scenario_2bus = {
            "name": "2-Bus Test",
            "grid_config": {"num_buses": 2},
            "generator_data": [
                {"id": "G1", "bus_id": 1, "capacity_mw": 100, "reserve_up_mw": 20, "reserve_down_mw": 15, "cost_energy_mwh": 20, "cost_reserve_up_mw": 2, "cost_reserve_down_mw": 1},
                {"id": "G2", "bus_id": 2, "capacity_mw": 50,  "reserve_up_mw": 10, "reserve_down_mw": 10, "cost_energy_mwh": 30, "cost_reserve_up_mw": 3, "cost_reserve_down_mw": 1.5}
            ],
            "load_data": [
                {"id": "L1", "bus_id": 2, "demand_mw": 70}
            ],
            "transmission_data": [
                {"id": "T1", "from_bus_id": 1, "to_bus_id": 2, "flow_limit_mw": 40}
            ],
            "system_requirements": {"reserve_up_mw": 7, "reserve_down_mw": 3.5}
        }

        self.sample_scenario_1bus_1gen_1load = {
            "name": "1-Bus Simple",
            "grid_config": {"num_buses": 1},
            "generator_data": [
                {"id": "G1", "bus_id": 1, "capacity_mw": 100, "cost_energy_mwh": 25, "reserve_up_mw": 10, "cost_reserve_up_mw": 2}
            ],
            "load_data": [
                {"id": "L1", "bus_id": 1, "demand_mw": 50}
            ],
            "transmission_data": [],
            "system_requirements": {"reserve_up_mw": 5} # 10% of demand
        }

    # --- Traditional Model Tests ---
    def test_traditional_prepare_input_data(self):
        parsed = traditional_model.prepare_input_data(self.sample_scenario_2bus)
        self.assertEqual(parsed['num_buses'], 2)
        self.assertEqual(parsed['num_generators'], 2)
        self.assertEqual(parsed['gen_bus_ids'][0], 0) # Check 0-indexing
        self.assertEqual(parsed['load_bus_ids'][0], 1)
        self.assertEqual(parsed['line_from_bus'][0], 0)
        self.assertEqual(parsed['line_to_bus'][0], 1)

    @patch('simulation_engine.traditional_model.linprog') # Mock scipy.optimize.linprog
    def test_traditional_solve_simple_case_predictable(self, mock_linprog):
        # For 1-bus, 1-gen (100MW cap, $25/MWh), 1-load (50MW), 5MW up-reserve req.
        # Expected: Gen=50MW, R_up=5MW. LMP = $25 (+ uplift for reserve if binding).
        # Reserve price = $2 if reserve constraint binding.

        # Mock the return value of linprog
        # Result object needs: success, x (solution vector), fun (objective value),
        #                    eqlin.marginals (nodal prices), ineqlin.marginals (reserve/other prices)
        # Vars: G1, R_up_G1, R_dn_G1 (no lines in 1-bus)
        # Constraints: G1+R_up <= 100, -G1+R_dn <= 0, -R_up <= -5
        mock_linprog.return_value = MagicMock(
            success=True,
            x=np.array([50, 5, 0]), # G1=50, R_up_G1=5, R_dn_G1=0
            fun=(50*25 + 5*2), # Total cost
            eqlin=MagicMock(marginals=np.array([-27])), # LMP = -(-27) = $27 (energy + reserve)
            ineqlin=MagicMock(marginals=np.array([0, 0, -2])) # G+R_up, G-R_dn, -Sum(R_up) <= -Req
        )

        parsed_data = traditional_model.prepare_input_data(self.sample_scenario_1bus_1gen_1load)
        solution = traditional_model.solve_traditional_market(parsed_data)

        self.assertEqual(solution['status'], 'success')
        self.assertAlmostEqual(solution['gen_power_mw'][0], 50)
        self.assertAlmostEqual(solution['gen_reserve_up_mw'][0], 5)
        self.assertAlmostEqual(solution['nodal_prices_mwh'][0], 27) # 25 (energy) + 2 (reserve)
        self.assertAlmostEqual(solution['system_up_reserve_price_mw'], 2)

    def test_traditional_run_simulation_end_to_end_simple(self):
        # This will use the actual linprog solver for a simple case
        results = traditional_model.run_traditional_simulation(self.sample_scenario_1bus_1gen_1load)

        self.assertEqual(results['status'], 'success')
        self.assertIn('operational_results', results)
        self.assertIn('financial_results', results)

        op_res = results['operational_results']
        fin_res = results['financial_results']

        self.assertAlmostEqual(op_res['gen_power_mw'][0], 50)
        self.assertAlmostEqual(op_res['gen_reserve_up_mw'][0], 5) # Should meet system_reserve_up_req

        # Price should be cost_energy + cost_reserve_up as gen is marginal for both
        expected_lmp = self.sample_scenario_1bus_1gen_1load['generator_data'][0]['cost_energy_mwh'] + \
                       self.sample_scenario_1bus_1gen_1load['generator_data'][0]['cost_reserve_up_mw']
        self.assertAlmostEqual(op_res['nodal_prices_mwh'][0], expected_lmp)
        self.assertAlmostEqual(op_res['system_up_reserve_price_mw'], self.sample_scenario_1bus_1gen_1load['generator_data'][0]['cost_reserve_up_mw'])

        gen_details = fin_res['generator_details'][0]
        # Profit = EnergyRev + ReserveRev - EnergyCost - ReserveCost
        # Profit = (50 * LMP) + (5 * R_price) - (50 * 25) - (5 * 2)
        # Profit = (50*27) + (5*2) - 1250 - 10 = 1350 + 10 - 1250 - 10 = 100 (uplift from reserve on inframarginal capacity)
        # Or, if LMP includes reserve component, then profit is just payment for capacity beyond marginal unit cost.
        # Here, the generator is marginal for both energy and reserve, so its profit should be near zero.
        # Let's re-evaluate: LMP is $27. Gen cost $25. Reserve price $2. Gen reserve cost $2.
        # Energy revenue: 50 * 27 = 1350. Cost: 50 * 25 = 1250. Energy profit = 100.
        # Reserve revenue: 5 * 2 = 10. Cost: 5 * 2 = 10. Reserve profit = 0.
        # Total profit = 100.
        self.assertAlmostEqual(gen_details['profit'], 100, places=1) # Allow for small LP solver variations

    # --- Causation Model Tests ---
    def test_causation_prepare_input_data(self):
        scenario_with_contingency = {**self.sample_scenario_2bus,
                                     "contingency_data": {"generator_outages": [{"generator_id": "G1"}]}}
        parsed = causation_model.prepare_causation_input_data(scenario_with_contingency)
        self.assertIn('contingencies', parsed)
        self.assertEqual(len(parsed['contingencies']['generator_outages']), 1)

    @patch('simulation_engine.causation_model.solve_base_case_dispatch') # Mock the traditional dispatch
    @patch('simulation_engine.causation_model.calculate_traditional_financials')
    def test_causation_run_simulation_simple_contingency(self, mock_calc_trad_financials, mock_solve_base):
        scenario_1bus_contingency = {
            "name": "1-Bus Causation",
            "grid_config": {"num_buses": 1},
            "generator_data": [
                {"id": "G1", "bus_id": 1, "capacity_mw": 100, "cost_energy_mwh": 20},
                {"id": "G2", "bus_id": 1, "capacity_mw": 50, "cost_energy_mwh": 30}
            ],
            "load_data": [{"id": "L1", "bus_id": 1, "demand_mw": 70}],
            "transmission_data": [],
            "system_requirements": {"reserve_up_mw": 0, "reserve_down_mw": 0}, # No reserves for simplicity
            "contingency_data": {"generator_outages": [{"generator_id": "G1"}]}
        }

        # Mock base case: G1 produces 70MW (cheaper), G2 produces 0.
        mock_solve_base.return_value = {
            'status': 'success',
            'gen_power_mw': np.array([70, 0]), # G1=70, G2=0
            'nodal_prices_mwh': np.array([20]), # LMP = G1 cost
            'total_cost': 70 * 20
        }
        # Mock traditional financials for base case
        mock_calc_trad_financials.return_value = {
            'generator_details': [
                {'id': 'G1', 'profit': 0, 'power_output_mw': 70}, # Assuming G1 is marginal
                {'id': 'G2', 'profit': 0, 'power_output_mw': 0}
            ],
            'system_summary': {'total_dispatch_cost': 1400}
        }

        results = causation_model.run_causation_simulation(scenario_1bus_contingency)

        self.assertEqual(results['status'], 'success')
        self.assertIn('contingency_analysis_details', results)

        contingency_res = results['contingency_analysis_details'].get('gen_outage_G1', {})
        self.assertTrue(any(v['type'] == 'demand_not_met' for v in contingency_res.get('violations', [])),
                        f"Expected demand_not_met. Violations: {contingency_res.get('violations')}")

        # Check if G2 (the remaining generator) is identified as a causer for the shortfall
        # In simplified model, if G2 was producing 0 in base case, it might not be marked as causer,
        # or its contribution factor might be 0. This depends on the exact identify_causers logic.
        # Current identify_causers_for_gen_outage only considers generators already online in base case.
        # If G2 produced 0, it won't be in causers. Let's verify this behavior.
        if contingency_res.get('causers'): # If causers dict is not empty
            self.assertNotIn('G2', contingency_res['causers'], "G2 should not be a causer if it was offline in base case by current simple logic")

        # If G2 was online in base case (e.g. G1=40, G2=30), then G2 would be a causer.
        # For this test, G2 was offline. Thus, no security charge on G2 for this specific causer logic.
        final_fin = results['final_causation_financials']
        g2_final_detail = next((g for g in final_fin['generator_details'] if g['id'] == 'G2'), None)
        if g2_final_detail:
            self.assertAlmostEqual(g2_final_detail.get('security_charge', 0), 0)


if __name__ == '__main__':
    unittest.main()
