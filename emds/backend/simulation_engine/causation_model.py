import numpy as np
from scipy.optimize import linprog
import copy
# Attempt to import from traditional_model for reuse, if possible
try:
    from .traditional_model import prepare_input_data as prepare_traditional_input_data
    from .traditional_model import solve_traditional_market as solve_base_case_dispatch
    # If we need to calculate financials from traditional model for base case
    from .traditional_model import calculate_financials as calculate_traditional_financials
except ImportError:
    print("Warning: Could not import from traditional_model. Ensure it's in the same package.")
    # Define dummy functions if import fails, to allow script to run for structure development
    def prepare_traditional_input_data(scenario_data): print("Dummy prepare_traditional_input_data"); return None
    def solve_base_case_dispatch(parsed_data): print("Dummy solve_base_case_dispatch"); return {'status': 'failure'}
    def calculate_traditional_financials(parsed_data, market_solution): print("Dummy calculate_traditional_financials"); return {}

# --- Constants for Simplified Violation Costs (Placeholders) ---
VALUE_OF_LOST_LOAD_MWH = 1000  # Cost per MWh of demand not met
LINE_OVERLOAD_PENALTY_MWH = 100 # Penalty per MWh of line overload (if monetized)

def prepare_causation_input_data(scenario_data):
    """
    Prepares input data for the causation model.
    Leverages traditional model's data prep and adds contingency specifics.
    """
    # Use the traditional input parser first
    parsed_data = prepare_traditional_input_data(scenario_data)
    if parsed_data is None: # Handle case where dummy was used
        return None

    # Add contingency data
    parsed_data['contingencies'] = scenario_data.get('contingency_data', {'generator_outages': [], 'line_outages': []})

    # Store original bus IDs (1-indexed) for easier mapping in results if needed
    parsed_data['original_gen_bus_ids'] = np.array([g['bus_id'] for g in scenario_data.get('generator_data', [])])
    parsed_data['original_load_bus_ids'] = np.array([l['bus_id'] for l in scenario_data.get('load_data', [])])
    parsed_data['original_line_from_bus'] = np.array([t['from_bus_id'] for t in scenario_data.get('transmission_data', [])])
    parsed_data['original_line_to_bus'] = np.array([t['to_bus_id'] for t in scenario_data.get('transmission_data', [])])

    return parsed_data

def check_violations(current_G, parsed_data, outaged_line_idx=None):
    """
    Highly simplified check for violations (demand not met, line overloads).
    This function needs a proper power flow calculation (e.g., DC power flow) for accuracy.
    For now, it will be very basic.

    Args:
        current_G (np.array): Current generator outputs.
        parsed_data (dict): Parsed scenario data.
        outaged_line_idx (int, optional): Index of a line that is outaged.

    Returns:
        list: A list of violation objects.
    """
    violations = []
    n_b = parsed_data['num_buses']
    n_t = parsed_data['num_lines']

    # 1. Demand Met Check (Simplified: Total generation vs Total demand)
    total_generation = np.sum(current_G)
    total_demand = np.sum(parsed_data['load_demand_mw'])
    demand_shortfall = total_demand - total_generation

    if demand_shortfall > 1e-3: # Using a small tolerance
        violations.append({
            'type': 'demand_not_met',
            'shortfall_mw': demand_shortfall,
            'cost': demand_shortfall * VALUE_OF_LOST_LOAD_MWH
        })
        # For simplicity, assume shortfall is distributed or at a specific bus if more detail needed
        # This doesn't identify WHICH bus has the shortfall without per-bus balance.

    # 2. Line Overload Check (Requires power flow calculation)
    # Placeholder: This is where a DC Power Flow would be calculated based on current_G
    # and network topology (PTDF matrix or Admittance matrix inversion).
    # For now, we don't have a readily available power flow calculation from the traditional model's output
    # (its line_flow_mw are decision variables of the LP, not calculated from G).
    # We will skip accurate line overload checks in this simplified version.
    # We could try to re-run a simplified dispatch or flow calculation here.

    # As a very rough proxy, if a line was heavily loaded in base case, and a nearby generator outages,
    # it *might* be overloaded. This is too speculative without actual flow calculation.
    # For now, this part will be mostly a placeholder.

    # If we had line flows `current_P_flows` calculated from `current_G` and network:
    # for i in range(n_t):
    #     if outaged_line_idx == i:
    #         continue # Skip the outaged line itself
    #     if abs(current_P_flows[i]) > parsed_data['line_flow_limit_mw'][i] + 1e-3: # Tolerance
    #         overload = abs(current_P_flows[i]) - parsed_data['line_flow_limit_mw'][i]
    #         violations.append({
    #             'type': 'line_overload',
    #             'line_id': parsed_data['line_ids'][i],
    #             'overload_mw': overload,
    #             'cost': overload * LINE_OVERLOAD_PENALTY_MWH # Simplified penalty
    #         })

    return violations


def identify_causers_for_gen_outage(parsed_data, base_G, base_P_flows, outaged_gen_id_str, violations):
    """
    Highly simplified identification of causers for a generator outage.
    This is a placeholder for a more sophisticated theory.
    """
    causers = {} # {generator_id_str: contribution_factor}

    # Example Simplistic Logic:
    # If demand is not met, all other operating generators that were producing in base case could be "causers"
    # for not ramping up enough (or not having enough capacity).
    # Their contribution could be proportional to their base_G.

    outaged_gen_idx = parsed_data['gen_ids'].index(outaged_gen_id_str)

    for violation in violations:
        if violation['type'] == 'demand_not_met':
            total_base_G_online = sum(g for i, g in enumerate(base_G) if i != outaged_gen_idx and g > 1e-3)
            if total_base_G_online > 1e-3:
                for i, gen_id_str in enumerate(parsed_data['gen_ids']):
                    if i == outaged_gen_idx or base_G[i] < 1e-3: # Skip outaged or non-producing gen
                        continue
                    contribution = base_G[i] / total_base_G_online
                    causers[gen_id_str] = causers.get(gen_id_str, 0) + contribution * violation['shortfall_mw']
                    # The 'value' here is their share of the shortfall_mw

    # If line overloads were identified, a different logic would apply, e.g., based on PTDFs or flow contributions.
    # For example, generators increasing flow on the overloaded line post-contingency.
    # Or generators that were heavily using the line pre-contingency.

    return causers

def analyze_contingencies(parsed_data, base_case_solution):
    """
    Analyzes defined contingencies.
    """
    if base_case_solution['status'] != 'success':
        print("Base case solution failed, cannot perform contingency analysis.")
        return {}

    base_G = base_case_solution['gen_power_mw']
    # base_P_flows from traditional model are LP variables, not direct calculations from G.
    # For a more accurate contingency analysis, P_flows should be recalculated based on G and network.
    # We'll pass base_P_flows but be mindful of this limitation.
    base_P_flows = base_case_solution.get('line_flow_mw', np.zeros(parsed_data['num_lines']))

    contingency_analysis = {}

    # Generator Outages
    for gen_outage_info in parsed_data['contingencies'].get('generator_outages', []):
        outaged_gen_id_str = gen_outage_info['generator_id']
        if outaged_gen_id_str not in parsed_data['gen_ids']:
            print(f"Warning: Outaged generator ID '{outaged_gen_id_str}' not found in generator list. Skipping.")
            continue

        outaged_gen_idx = parsed_data['gen_ids'].index(outaged_gen_id_str)

        print(f"\nAnalyzing Generator Outage: {outaged_gen_id_str} (Index: {outaged_gen_idx})")

        # Simulate post-contingency state (simplified)
        G_post_contingency = np.copy(base_G)
        lost_generation = G_post_contingency[outaged_gen_idx]
        G_post_contingency[outaged_gen_idx] = 0
        print(f"  Lost generation from {outaged_gen_id_str}: {lost_generation:.2f} MW")

        # Here, a re-dispatch or at least a call to a power flow routine should occur.
        # For now, we use the simplified check_violations.
        # P_flows_post_contingency would be recalculated based on G_post_contingency.

        violations = check_violations(G_post_contingency, parsed_data)

        current_analysis = {'violations': violations, 'causers': {}}
        if violations:
            print(f"  Violations found for outage of {outaged_gen_id_str}: {violations}")
            # Identify causers (highly simplified)
            causers = identify_causers_for_gen_outage(parsed_data, base_G, base_P_flows, outaged_gen_id_str, violations)
            current_analysis['causers'] = causers
            print(f"  Identified causers: {causers}")
        else:
            print(f"  No violations (simplified check) for outage of {outaged_gen_id_str}.")

        contingency_analysis[f"gen_outage_{outaged_gen_id_str}"] = current_analysis

    # Line Outages (More Complex - Placeholder)
    for line_outage_info in parsed_data['contingencies'].get('line_outages', []):
        outaged_line_id_str = line_outage_info['line_id']
        if outaged_line_id_str not in parsed_data['line_ids']:
            print(f"Warning: Outaged line ID '{outaged_line_id_str}' not found in line list. Skipping.")
            continue

        outaged_line_idx = parsed_data['line_ids'].index(outaged_line_id_str)
        print(f"\nAnalyzing Line Outage: {outaged_line_id_str} (Index: {outaged_line_idx}) - Placeholder")
        # Simulating line outages properly requires modifying the network topology (e.g. PTDF matrix or Ybus)
        # and re-running a power flow or dispatch. This is beyond current simplified scope.
        # For now, we'll just record the event.

        # G_post_line_contingency = np.copy(base_G) # Assume G doesn't change immediately without re-dispatch
        # violations = check_violations(G_post_line_contingency, parsed_data, outaged_line_idx=outaged_line_idx)

        contingency_analysis[f"line_outage_{outaged_line_id_str}"] = {
            'violations': [{'type': 'line_outage_analysis_placeholder', 'description': 'Detailed analysis for line outage not implemented'}],
            'causers': {}
        }
        print(f"  Line outage analysis for {outaged_line_id_str} is a placeholder.")

    return contingency_analysis


def calculate_causation_based_financials(parsed_data, base_case_solution, traditional_financials, contingency_analysis_results):
    """
    Calculates final financial outcomes including security charges.
    """
    final_financials = copy.deepcopy(traditional_financials) # Start with traditional results
    if not final_financials or 'generator_details' not in final_financials: # Handle dummy data case
        # Initialize a basic structure if traditional_financials is empty or malformed
        final_financials = {'generator_details': [{'id': gid, 'profit': 0, 'security_charge': 0} for gid in parsed_data['gen_ids']],
                            'system_summary': {'total_security_charges': 0}}


    # Initialize security charges
    for gen_detail in final_financials.get('generator_details', []):
        gen_detail['security_charge'] = 0

    total_security_charges_collected = 0

    for contingency_id, analysis in contingency_analysis_results.items():
        if not analysis['violations'] or not analysis['causers']:
            continue

        # Calculate total cost of this contingency's violations
        contingency_total_cost = sum(v.get('cost', 0) for v in analysis['violations'])
        if contingency_total_cost == 0:
            continue

        print(f"Processing contingency {contingency_id} with cost {contingency_total_cost:.2f}")

        # Allocate costs to causers
        # The 'causers' dict currently stores share of shortfall_mw. We need to normalize this.
        # This logic needs to be robust based on how causer contributions are defined.
        # For now, let's assume causer values are weights for allocating contingency_total_cost

        total_causer_contribution_value = sum(analysis['causers'].values()) # Sum of shortfall_mw shares

        if total_causer_contribution_value > 1e-6: # Avoid division by zero
            for gen_id_str, contribution_value in analysis['causers'].items():
                allocated_cost = (contribution_value / total_causer_contribution_value) * contingency_total_cost

                # Find the generator in final_financials and add the charge
                for gen_detail in final_financials.get('generator_details',[]):
                    if gen_detail['id'] == gen_id_str:
                        gen_detail['security_charge'] = gen_detail.get('security_charge',0) + allocated_cost
                        gen_detail['profit'] = gen_detail.get('profit',0) - allocated_cost # Adjust profit
                        total_security_charges_collected += allocated_cost
                        print(f"  Allocated security charge {allocated_cost:.2f} to {gen_id_str} for {contingency_id}")
                        break

    if 'system_summary' not in final_financials: final_financials['system_summary'] = {}
    final_financials['system_summary']['total_security_charges_collected'] = total_security_charges_collected
    # Note: Revenue neutrality is a complex topic. Here, security charges are collected from generators.
    # How these charges are used (e.g., to pay for corrective actions, compensate harmed parties) is not defined.

    return final_financials


def run_causation_simulation(scenario_data_input):
    """
    Main function to run the causation-based simulation.
    """
    print("--- Starting Causation-Based Simulation ---")

    # 0. Make a deep copy of scenario data to avoid modifying the original
    scenario_data = copy.deepcopy(scenario_data_input)

    # 1. Prepare Data
    print("\n[Phase 1: Preparing Input Data]")
    parsed_data = prepare_causation_input_data(scenario_data)
    if parsed_data is None or 'num_generators' not in parsed_data : # Check if dummy was used or basic parsing failed
        return {"error": "Failed to prepare input data for causation model."}


    # 2. Base Case Economic Dispatch (using traditional model)
    print("\n[Phase 2: Running Base Case Dispatch]")
    # Ensure system reserve requirements are reasonable for base case if not specified well
    if 'system_reserve_up_req' not in parsed_data or parsed_data['system_reserve_up_req'] is None:
        parsed_data['system_reserve_up_req'] = np.sum(parsed_data['load_demand_mw']) * 0.05 # default
    if 'system_reserve_down_req' not in parsed_data or parsed_data['system_reserve_down_req'] is None:
        parsed_data['system_reserve_down_req'] = np.sum(parsed_data['load_demand_mw']) * 0.05 # default

    base_case_solution = solve_base_case_dispatch(parsed_data)
    if base_case_solution['status'] != 'success':
        error_msg = f"Base case dispatch failed: {base_case_solution.get('message', 'Unknown error')}"
        print(f"  Error: {error_msg}")
        return {"error": error_msg, "details": base_case_solution}
    print("  Base case dispatch successful.")

    # Calculate traditional financials for the base case
    print("\n[Phase 3: Calculating Traditional Financials for Base Case]")
    traditional_financials = calculate_traditional_financials(parsed_data, base_case_solution)
    if not traditional_financials: # Handle dummy function case
         traditional_financials = {'generator_details': [{'id': gid, 'profit': 0} for gid in parsed_data['gen_ids']],
                                   'system_summary': {}} # basic structure
    print("  Traditional financials calculated.")


    # 3. Contingency Analysis
    print("\n[Phase 4: Analyzing Contingencies]")
    contingency_analysis_results = analyze_contingencies(parsed_data, base_case_solution)
    print("  Contingency analysis completed.")

    # 4. Calculate Causation-Based Financials (Security Charges, Differentiated Prices)
    print("\n[Phase 5: Calculating Causation-Based Financials]")
    final_results = calculate_causation_based_financials(parsed_data, base_case_solution, traditional_financials, contingency_analysis_results)
    print("  Causation-based financials calculated.")

    # Add base case and contingency analysis to the final results for completeness
    final_results['base_case_dispatch_solution'] = base_case_solution
    final_results['contingency_analysis_details'] = contingency_analysis_results
    final_results['parsed_input_for_causation'] = parsed_data # For debugging or deeper inspection

    print("\n--- Causation-Based Simulation Finished ---")
    return final_results


# --- Example Usage ---
if __name__ == '__main__':
    # Sample scenario_data (e.g., 2 buses, 2 generators, 1 load, 1 line)
    sample_scenario_for_causation = {
        "name": "Causation Test Case",
        "grid_config": {"num_buses": 2}, # Must match the bus IDs used
        "generator_data": [
            {"id": "G1", "bus_id": 1, "capacity_mw": 100, "reserve_up_mw": 20, "reserve_down_mw": 15, "cost_energy_mwh": 20, "cost_reserve_up_mw": 2, "cost_reserve_down_mw": 1},
            {"id": "G2", "bus_id": 2, "capacity_mw": 50,  "reserve_up_mw": 10, "reserve_down_mw": 10, "cost_energy_mwh": 30, "cost_reserve_up_mw": 3, "cost_reserve_down_mw": 1.5}
        ],
        "load_data": [
            {"id": "L1", "bus_id": 2, "demand_mw": 70} # Total demand = 70 MW
        ],
        "transmission_data": [
            {"id": "T1", "from_bus_id": 1, "to_bus_id": 2, "flow_limit_mw": 40} # Line from Bus 1 to Bus 2
        ],
        "system_requirements": {
            "reserve_up_mw": 7, # 10% of 70
            "reserve_down_mw": 3.5 # 5% of 70
        },
        "contingency_data": {
            "generator_outages": [
                {"generator_id": "G1", "description": "Outage of Generator G1"}
                # {"generator_id": "G2", "description": "Outage of Generator G2"} # Can add more
            ],
            "line_outages": [
                # {"line_id": "T1", "description": "Outage of Transmission Line T1"} # Placeholder
            ]
        }
    }

    results = run_causation_simulation(sample_scenario_for_causation)

    print("\n\n--- FINAL CAUSATION SIMULATION RESULTS ---")
    import json

    # Custom serializer to handle numpy arrays for JSON dump if any slip through (though most are converted)
    class NumpyEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            if isinstance(obj, (np.float32, np.float64, np.int32, np.int64)):
                return float(obj) # or int(obj)
            return json.JSONEncoder.default(self, obj)

    print(json.dumps(results, indent=2, cls=NumpyEncoder))

    if results.get("error"):
        print(f"\nSimulation failed with error: {results['error']}")
    elif results.get('base_case_dispatch_solution', {}).get('status') == 'success':
        print("\n--- Key Metrics from Causation Model ---")
        if 'system_summary' in results:
             print(f"Total Dispatch Cost (Base Case): {results['base_case_dispatch_solution'].get('total_cost', 'N/A'):.2f}")
             print(f"Total Security Charges Collected: {results['system_summary'].get('total_security_charges_collected', 'N/A'):.2f}")

        for gen_detail in results.get('generator_details', []):
            print(f"Generator {gen_detail['id']}: Profit (after security) = {gen_detail.get('profit', 'N/A'):.2f}, Security Charge = {gen_detail.get('security_charge', 'N/A'):.2f}")

        # Example assertion for the test case
        # If G1 outages (100MW cap, 20 cost) and L1 demands 70MW, G2 (50MW cap, 30 cost) cannot meet demand alone.
        # Expect demand_not_met violation.
        if "gen_outage_G1" in results.get("contingency_analysis_details", {}):
            g1_analysis = results["contingency_analysis_details"]["gen_outage_G1"]
            assert any(v['type'] == 'demand_not_met' for v in g1_analysis.get('violations', [])), "Expected demand_not_met for G1 outage"
            if any(v['type'] == 'demand_not_met' for v in g1_analysis.get('violations', [])):
                 print("Successfully detected demand_not_met for G1 outage as expected.")

            # If G2 was the only one left and produced, it should be marked as a causer for the shortfall.
            if g1_analysis.get('causers', {}).get('G2', 0) > 0 :
                 print("G2 correctly identified as a causer for G1 outage shortfall (simplified logic).")
            # else: # G2 might not be a "causer" if it produced its max and couldn't cover. Logic dependent.
            #     print(f"G2 causer info for G1 outage: {g1_analysis.get('causers', {}).get('G2')}")


    print("\n--- End of Example ---")
