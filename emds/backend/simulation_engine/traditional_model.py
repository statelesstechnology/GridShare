import numpy as np
from scipy.optimize import linprog

def prepare_input_data(scenario_data):
    """
    Parses scenario data and prepares it for the optimization model.
    """
    # Extract basic counts
    num_buses = scenario_data.get('grid_config', {}).get('num_buses', 0)

    raw_generators = scenario_data.get('generator_data', [])
    raw_loads = scenario_data.get('load_data', [])
    raw_lines = scenario_data.get('transmission_data', [])

    num_generators = len(raw_generators)
    num_loads = len(raw_loads)
    num_lines = len(raw_lines)

    # Process generators
    gen_ids = [g['id'] for g in raw_generators]
    gen_bus_ids = np.array([g['bus_id'] for g in raw_generators]) # Bus IDs are 1-indexed from input
    gen_capacity_mw = np.array([g['capacity_mw'] for g in raw_generators])
    gen_reserve_up_mw = np.array([g.get('reserve_up_mw', g['capacity_mw']) for g in raw_generators]) # Default to capacity if not specified
    gen_reserve_down_mw = np.array([g.get('reserve_down_mw', g['capacity_mw']) for g in raw_generators]) # Default to capacity
    gen_cost_energy_mwh = np.array([g['cost_energy_mwh'] for g in raw_generators])
    gen_cost_reserve_up_mw = np.array([g.get('cost_reserve_up_mw', 0) for g in raw_generators]) # Default to 0 if not specified
    gen_cost_reserve_down_mw = np.array([g.get('cost_reserve_down_mw', 0) for g in raw_generators]) # Default to 0

    # Process loads
    load_ids = [l['id'] for l in raw_loads]
    load_bus_ids = np.array([l['bus_id'] for l in raw_loads]) # Bus IDs are 1-indexed
    load_demand_mw = np.array([l['demand_mw'] for l in raw_loads])

    # Process lines
    line_ids = [t['id'] for t in raw_lines]
    line_from_bus = np.array([t['from_bus_id'] for t in raw_lines]) # Bus IDs are 1-indexed
    line_to_bus = np.array([t['to_bus_id'] for t in raw_lines]) # Bus IDs are 1-indexed
    line_flow_limit_mw = np.array([t['flow_limit_mw'] for t in raw_lines])
    line_cost_mw_flow = np.array([t.get('cost_mw_flow', 0) for t in raw_lines]) # Default to 0

    # System reserve requirements (placeholders - should ideally come from scenario_data)
    # For example, 10% of total demand for up-reserve, 5% for down-reserve
    total_demand = np.sum(load_demand_mw)
    system_reserve_up_req = scenario_data.get('system_requirements', {}).get('reserve_up_mw', total_demand * 0.10)
    system_reserve_down_req = scenario_data.get('system_requirements', {}).get('reserve_down_mw', total_demand * 0.05)

    # Ensure bus IDs are 0-indexed for internal use if necessary, or manage mapping
    # For this model, we'll use 0 to num_buses-1 indexing for matrices.
    # The input bus_ids are typically 1-based. We need to be careful with this.
    # Let's assume bus_ids in scenario_data are 1 to N. We'll convert to 0 to N-1 for matrix construction.

    parsed_data = {
        'num_buses': num_buses,
        'num_generators': num_generators,
        'num_loads': num_loads,
        'num_lines': num_lines,

        'gen_ids': gen_ids,
        'gen_bus_ids': gen_bus_ids - 1, # Convert to 0-indexed
        'gen_capacity_mw': gen_capacity_mw,
        'gen_reserve_up_mw': gen_reserve_up_mw,
        'gen_reserve_down_mw': gen_reserve_down_mw,
        'gen_cost_energy_mwh': gen_cost_energy_mwh,
        'gen_cost_reserve_up_mw': gen_cost_reserve_up_mw,
        'gen_cost_reserve_down_mw': gen_cost_reserve_down_mw,

        'load_ids': load_ids,
        'load_bus_ids': load_bus_ids - 1, # Convert to 0-indexed
        'load_demand_mw': load_demand_mw,

        'line_ids': line_ids,
        'line_from_bus': line_from_bus - 1, # Convert to 0-indexed
        'line_to_bus': line_to_bus - 1, # Convert to 0-indexed
        'line_flow_limit_mw': line_flow_limit_mw,
        'line_cost_mw_flow': line_cost_mw_flow,

        'system_reserve_up_req': system_reserve_up_req,
        'system_reserve_down_req': system_reserve_down_req,
    }
    return parsed_data

def solve_traditional_market(parsed_data):
    """
    Sets up and solves the linear programming problem for the traditional market model.
    """
    n_g = parsed_data['num_generators']
    n_l = parsed_data['num_loads'] # Not directly used in decision vars if demand is fixed
    n_t = parsed_data['num_lines']
    n_b = parsed_data['num_buses']

    # Decision variables:
    # 1. Generator power output G_i (n_g)
    # 2. Generator up-reserve R_g_up_i (n_g)
    # 3. Generator down-reserve R_g_dn_i (n_g)
    # 4. Line power flows P_l (n_t) - positive flow from from_bus to to_bus

    num_vars = n_g * 3 + n_t

    # --- Objective Function (c vector) ---
    c = np.zeros(num_vars)
    # Generator energy costs
    c[0:n_g] = parsed_data['gen_cost_energy_mwh']
    # Generator up-reserve costs
    c[n_g : n_g*2] = parsed_data['gen_cost_reserve_up_mw']
    # Generator down-reserve costs
    c[n_g*2 : n_g*3] = parsed_data['gen_cost_reserve_down_mw']
    # Line flow costs (if any)
    c[n_g*3 : n_g*3 + n_t] = parsed_data['line_cost_mw_flow']

    # --- Bounds for Decision Variables ---
    bounds = []
    # G_i bounds: 0 <= G_i <= capacity_mw_i
    for i in range(n_g):
        bounds.append((0, parsed_data['gen_capacity_mw'][i]))
    # R_g_up_i bounds: 0 <= R_g_up_i <= reserve_up_mw_i
    for i in range(n_g):
        bounds.append((0, parsed_data['gen_reserve_up_mw'][i]))
    # R_g_dn_i bounds: 0 <= R_g_dn_i <= reserve_down_mw_i
    for i in range(n_g):
        bounds.append((0, parsed_data['gen_reserve_down_mw'][i]))
    # P_l bounds: -flow_limit_mw_l <= P_l <= flow_limit_mw_l
    for i in range(n_t):
        bounds.append((-parsed_data['line_flow_limit_mw'][i], parsed_data['line_flow_limit_mw'][i]))

    # --- Equality Constraints (A_eq, b_eq) - Power Balance at each bus ---
    # For each bus k: sum(G_i for gen_i at bus_k) - sum(D_j for load_j at bus_k)
    #                - sum(P_l for lines_l leaving bus_k) + sum(P_l for lines_l entering bus_k) = 0

    A_eq = np.zeros((n_b, num_vars))
    b_eq = np.zeros(n_b)

    # Populate fixed demand part of b_eq
    for k in range(n_b): # For each bus
        bus_loads_sum = 0
        for ld_idx in range(parsed_data['num_loads']):
            if parsed_data['load_bus_ids'][ld_idx] == k:
                bus_loads_sum += parsed_data['load_demand_mw'][ld_idx]
        b_eq[k] = bus_loads_sum # Demand is on the RHS

    # Populate A_eq
    for k in range(n_b): # For each bus
        # Generator contributions
        for g_idx in range(n_g):
            if parsed_data['gen_bus_ids'][g_idx] == k:
                A_eq[k, g_idx] = 1 # G_i at bus k

        # Line flow contributions
        for t_idx in range(n_t):
            if parsed_data['line_from_bus'][t_idx] == k: # Line leaves bus k
                A_eq[k, n_g*3 + t_idx] = 1 # P_l (outgoing flow is positive)
            if parsed_data['line_to_bus'][t_idx] == k:   # Line enters bus k
                A_eq[k, n_g*3 + t_idx] = -1 # P_l (incoming flow is negative of positive outgoing)

    # --- Inequality Constraints (A_ub, b_ub) ---
    # Number of inequality constraints:
    # 1. G_i + R_g_up_i <= capacity_mw_i  (n_g constraints)
    # 2. G_i - R_g_dn_i >= 0  => -G_i + R_g_dn_i <= 0 (n_g constraints)
    # 3. sum(R_g_up_i) >= TotalUpReserveReq => -sum(R_g_up_i) <= -TotalUpReserveReq (1 constraint)
    # 4. sum(R_g_dn_i) >= TotalDownReserveReq => -sum(R_g_dn_i) <= -TotalDownReserveReq (1 constraint)
    num_ineq_constraints = n_g * 2 + 2
    A_ub = np.zeros((num_ineq_constraints, num_vars))
    b_ub = np.zeros(num_ineq_constraints)

    current_row = 0
    # 1. G_i + R_g_up_i <= capacity_mw_i
    for i in range(n_g):
        A_ub[current_row, i] = 1          # G_i
        A_ub[current_row, n_g + i] = 1    # R_g_up_i
        b_ub[current_row] = parsed_data['gen_capacity_mw'][i]
        current_row += 1

    # 2. -G_i + R_g_dn_i <= 0  (equivalent to G_i - R_g_dn_i >= 0)
    for i in range(n_g):
        A_ub[current_row, i] = -1         # -G_i
        A_ub[current_row, n_g*2 + i] = 1  # R_g_dn_i
        b_ub[current_row] = 0
        current_row += 1

    # 3. -sum(R_g_up_i) <= -TotalUpReserveReq
    for i in range(n_g):
        A_ub[current_row, n_g + i] = -1 # -R_g_up_i
    b_ub[current_row] = -parsed_data['system_reserve_up_req']
    current_row += 1

    # 4. -sum(R_g_dn_i) <= -TotalDownReserveReq
    for i in range(n_g):
        A_ub[current_row, n_g*2 + i] = -1 # -R_g_dn_i
    b_ub[current_row] = -parsed_data['system_reserve_down_req']
    current_row += 1

    # --- Solve the LP ---
    print("Solving LP...")
    # Note: SciPy's linprog default method 'interior-point' can be slow or less stable for some problems.
    # 'highs' is generally recommended if available (SciPy 1.6.0+).
    # 'highs-ds' (Dual Simplex) or 'highs-ipm' (Interior Point) can also be specified.
    result = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method='highs')

    solution = {}
    if result.success:
        print("Optimization successful.")
        x = result.x
        solution['status'] = 'success'
        solution['total_cost'] = result.fun

        solution['gen_power_mw'] = x[0:n_g]
        solution['gen_reserve_up_mw'] = x[n_g : n_g*2]
        solution['gen_reserve_down_mw'] = x[n_g*2 : n_g*3]
        solution['line_flow_mw'] = x[n_g*3 : n_g*3 + n_t]

        # Duals (Marginals)
        # For equality constraints (A_eq @ x = b_eq), these are the shadow prices (e.g., LMP at buses)
        # Sign convention: SciPy's duals for A_eq x = b_eq are typically such that if b_eq increases, objective increases by dual.
        # LMP is often defined as -dual of power balance equation.
        solution['nodal_prices_mwh'] = -result.eqlin.marginals if result.eqlin is not None else np.zeros(n_b)

        # Duals for inequality constraints (A_ub @ x <= b_ub)
        # Price for up-reserve capacity: marginal of sum(R_g_up_i) >= TotalUpReserveReq
        # Price for down-reserve capacity: marginal of sum(R_g_dn_i) >= TotalDownReserveReq
        # These are the last two inequality constraints.
        # SciPy's marginals for A_ub x <= b_ub are non-positive. A positive shadow price means the constraint is binding.
        # The shadow price of sum(R_up) >= Req_up (which is -sum(R_up) <= -Req_up) would be -result.ineqlin.marginals[-2]
        if result.ineqlin is not None and len(result.ineqlin.marginals) == num_ineq_constraints:
            solution['system_up_reserve_price_mw'] = -result.ineqlin.marginals[-2]
            solution['system_down_reserve_price_mw'] = -result.ineqlin.marginals[-1]
            # Other marginals (e.g. for G+R_up <= Cap) can also be extracted if needed
            solution['gen_capacity_shadow_price'] = -result.ineqlin.marginals[0:n_g] # for G+R_up <= Cap
            solution['gen_min_output_shadow_price'] = -result.ineqlin.marginals[n_g:n_g*2] # for G-R_dn >= 0

        else:
            solution['system_up_reserve_price_mw'] = 0
            solution['system_down_reserve_price_mw'] = 0
            solution['gen_capacity_shadow_price'] = np.zeros(n_g)
            solution['gen_min_output_shadow_price'] = np.zeros(n_g)

    else:
        print(f"Optimization failed: {result.message}")
        solution['status'] = 'failure'
        solution['message'] = result.message
        # Initialize arrays to prevent key errors later
        solution['gen_power_mw'] = np.zeros(n_g)
        solution['gen_reserve_up_mw'] = np.zeros(n_g)
        solution['gen_reserve_down_mw'] = np.zeros(n_g)
        solution['line_flow_mw'] = np.zeros(n_t)
        solution['nodal_prices_mwh'] = np.zeros(n_b)
        solution['system_up_reserve_price_mw'] = 0
        solution['system_down_reserve_price_mw'] = 0
        solution['gen_capacity_shadow_price'] = np.zeros(n_g)
        solution['gen_min_output_shadow_price'] = np.zeros(n_g)

    return solution

def calculate_financials(parsed_data, market_solution):
    """
    Calculates financial outcomes for generators and loads based on market solution.
    """
    if market_solution['status'] != 'success':
        return {"error": "Market solution was not successful."}

    n_g = parsed_data['num_generators']
    n_l = parsed_data['num_loads']

    gen_profits = np.zeros(n_g)
    gen_revenue_energy = np.zeros(n_g)
    gen_revenue_reserve_up = np.zeros(n_g)
    gen_revenue_reserve_down = np.zeros(n_g)
    gen_cost_total = np.zeros(n_g)

    # Generator financials
    for i in range(n_g):
        bus_idx = parsed_data['gen_bus_ids'][i] # 0-indexed bus ID
        lmp_at_gen_bus = market_solution['nodal_prices_mwh'][bus_idx]

        # Revenue from energy
        gen_revenue_energy[i] = market_solution['gen_power_mw'][i] * lmp_at_gen_bus
        # Revenue from up-reserve
        gen_revenue_reserve_up[i] = market_solution['gen_reserve_up_mw'][i] * market_solution['system_up_reserve_price_mw']
        # Revenue from down-reserve
        gen_revenue_reserve_down[i] = market_solution['gen_reserve_down_mw'][i] * market_solution['system_down_reserve_price_mw']

        total_revenue = gen_revenue_energy[i] + gen_revenue_reserve_up[i] + gen_revenue_reserve_down[i]

        # Costs
        cost_of_energy_produced = market_solution['gen_power_mw'][i] * parsed_data['gen_cost_energy_mwh'][i]
        cost_of_reserve_up_provided = market_solution['gen_reserve_up_mw'][i] * parsed_data['gen_cost_reserve_up_mw'][i]
        cost_of_reserve_down_provided = market_solution['gen_reserve_down_mw'][i] * parsed_data['gen_cost_reserve_down_mw'][i]
        gen_cost_total[i] = cost_of_energy_produced + cost_of_reserve_up_provided + cost_of_reserve_down_provided

        gen_profits[i] = total_revenue - gen_cost_total[i]

    # Consumer payments
    consumer_payments = np.zeros(n_l)
    for j in range(n_l):
        bus_idx = parsed_data['load_bus_ids'][j] # 0-indexed bus ID
        lmp_at_load_bus = market_solution['nodal_prices_mwh'][bus_idx]
        consumer_payments[j] = parsed_data['load_demand_mw'][j] * lmp_at_load_bus

    total_system_cost_dispatch = market_solution['total_cost'] # From LP objective value
    total_generator_revenue = np.sum(gen_revenue_energy) + np.sum(gen_revenue_reserve_up) + np.sum(gen_revenue_reserve_down)
    total_consumer_payment = np.sum(consumer_payments)

    # Uplift or "missing money" - difference between what consumers pay and what generators earn from energy only
    # This is a simplified view; true uplift includes congestion rents, reserve payments etc.
    congestion_rent = total_consumer_payment - np.sum(gen_revenue_energy) # If only considering energy market
                                                                          # More accurately, sum(P_l * (LMP_to - LMP_from))

    results = {
        'generator_details': [],
        'load_details': [],
        'line_details': [],
        'system_summary': {
            'total_dispatch_cost': total_system_cost_dispatch,
            'total_generator_revenue': total_generator_revenue,
            'total_consumer_payment_for_energy': total_consumer_payment, # Payment for energy at LMP
            'total_energy_generation_mw': np.sum(market_solution['gen_power_mw']),
            'total_demand_mw': np.sum(parsed_data['load_demand_mw']),
            'total_up_reserve_mw': np.sum(market_solution['gen_reserve_up_mw']),
            'total_down_reserve_mw': np.sum(market_solution['gen_reserve_down_mw']),
            'system_up_reserve_price_mw': market_solution['system_up_reserve_price_mw'],
            'system_down_reserve_price_mw': market_solution['system_down_reserve_price_mw'],
            'congestion_rent_approx': congestion_rent # Simplified
        }
    }

    for i in range(n_g):
        results['generator_details'].append({
            'id': parsed_data['gen_ids'][i],
            'bus_id': parsed_data['gen_bus_ids'][i] + 1, # Back to 1-indexed for output
            'power_output_mw': market_solution['gen_power_mw'][i],
            'reserve_up_mw': market_solution['gen_reserve_up_mw'][i],
            'reserve_down_mw': market_solution['gen_reserve_down_mw'][i],
            'lmp_at_bus_mwh': market_solution['nodal_prices_mwh'][parsed_data['gen_bus_ids'][i]],
            'cost_of_dispatch_mwh': parsed_data['gen_cost_energy_mwh'][i],
            'revenue_energy_mwh': gen_revenue_energy[i],
            'revenue_reserve_up_mw': gen_revenue_reserve_up[i],
            'revenue_reserve_down_mw': gen_revenue_reserve_down[i],
            'total_cost': gen_cost_total[i],
            'profit': gen_profits[i]
        })

    for j in range(n_l):
        results['load_details'].append({
            'id': parsed_data['load_ids'][j],
            'bus_id': parsed_data['load_bus_ids'][j] + 1, # Back to 1-indexed
            'demand_mw': parsed_data['load_demand_mw'][j],
            'lmp_at_bus_mwh': market_solution['nodal_prices_mwh'][parsed_data['load_bus_ids'][j]],
            'payment_for_energy': consumer_payments[j]
        })

    for k in range(n_t):
        results['line_details'].append({
            'id': parsed_data['line_ids'][k],
            'from_bus': parsed_data['line_from_bus'][k] + 1, # Back to 1-indexed
            'to_bus': parsed_data['line_to_bus'][k] + 1, # Back to 1-indexed
            'flow_mw': market_solution['line_flow_mw'][k],
            'flow_limit_mw': parsed_data['line_flow_limit_mw'][k],
            'lmp_from_bus': market_solution['nodal_prices_mwh'][parsed_data['line_from_bus'][k]],
            'lmp_to_bus': market_solution['nodal_prices_mwh'][parsed_data['line_to_bus'][k]],
            'congestion_value_approx': market_solution['line_flow_mw'][k] * (market_solution['nodal_prices_mwh'][parsed_data['line_to_bus'][k]] - market_solution['nodal_prices_mwh'][parsed_data['line_from_bus'][k]])
        })

    # Add nodal prices to system summary
    results['system_summary']['nodal_prices_mwh'] = {f"Bus_{i+1}": price for i, price in enumerate(market_solution['nodal_prices_mwh'])}

    return results

# --- Example Usage ---
if __name__ == '__main__':
    # Sample scenario_data (e.g., 2 buses, 2 generators, 1 load, 1 line)
    sample_scenario_data = {
        "name": "Simple Test Case",
        "grid_config": {"num_buses": 2},
        "generator_data": [
            {"id": "G1", "bus_id": 1, "capacity_mw": 100, "reserve_up_mw": 20, "reserve_down_mw": 15, "cost_energy_mwh": 20, "cost_reserve_up_mw": 2, "cost_reserve_down_mw": 1},
            {"id": "G2", "bus_id": 2, "capacity_mw": 50,  "reserve_up_mw": 10, "reserve_down_mw": 10, "cost_energy_mwh": 30, "cost_reserve_up_mw": 3, "cost_reserve_down_mw": 1.5}
        ],
        "load_data": [
            {"id": "L1", "bus_id": 2, "demand_mw": 70}
        ],
        "transmission_data": [
            {"id": "T1", "from_bus_id": 1, "to_bus_id": 2, "flow_limit_mw": 40, "cost_mw_flow": 0.1} # Added small line cost
        ],
        "system_requirements": { # Optional: if not provided, defaults will be used
            "reserve_up_mw": 10, # 10% of 70 demand = 7. Adjusted for testing
            "reserve_down_mw": 5  # 5% of 70 demand = 3.5. Adjusted for testing
        }
    }

    print("--- Preparing Input Data ---")
    parsed_market_data = prepare_input_data(sample_scenario_data)
    # print(f"Parsed Data: {parsed_market_data}")

    print("\n--- Solving Traditional Market ---")
    market_solution = solve_traditional_market(parsed_market_data)
    # print(f"Market Solution: {market_solution}")

    if market_solution['status'] == 'success':
        print("\n--- Calculating Financials ---")
        financial_results = calculate_financials(parsed_market_data, market_solution)

        print("\n--- Simulation Results ---")
        import json
        print(json.dumps(financial_results, indent=2))

        # Specific checks:
        print(f"\nTotal Demand: {financial_results['system_summary']['total_demand_mw']}")
        print(f"Total Generation: {financial_results['system_summary']['total_energy_generation_mw']}")
        assert np.isclose(financial_results['system_summary']['total_demand_mw'], financial_results['system_summary']['total_energy_generation_mw']), "Generation should meet demand"

        print(f"System Up Reserve Provided: {financial_results['system_summary']['total_up_reserve_mw']}")
        print(f"System Up Reserve Required: {parsed_market_data['system_reserve_up_req']}")
        assert financial_results['system_summary']['total_up_reserve_mw'] >= parsed_market_data['system_reserve_up_req'] - 1e-5, "Up reserve requirement not met" # Tolerance for LP solver

        print(f"System Down Reserve Provided: {financial_results['system_summary']['total_down_reserve_mw']}")
        print(f"System Down Reserve Required: {parsed_market_data['system_reserve_down_req']}")
        assert financial_results['system_summary']['total_down_reserve_mw'] >= parsed_market_data['system_reserve_down_req'] - 1e-5, "Down reserve requirement not met"

    else:
        print(f"Could not calculate financials because market solution failed: {market_solution.get('message')}")


def run_traditional_simulation(scenario_dict):
    """
    Main entry point for running a traditional simulation.
    Takes a scenario dictionary, runs the simulation, and returns results.
    """
    try:
        parsed_data = prepare_input_data(scenario_dict)
        if not parsed_data: # Or check a key field like 'num_buses' if it can be 0
            return {"error": "Failed to parse scenario data.", "details": "Parsed data is empty or invalid."}

        market_solution = solve_traditional_market(parsed_data)

        # The 'status' field in market_solution is 'success' or 'failure' (custom)
        # linprog result.status == 0 means success for scipy.optimize.linprog
        # We are using our custom 'status' string.
        if market_solution.get('status') == 'success':
            financial_results = calculate_financials(parsed_data, market_solution)
            # Combine all results into a single dictionary
            # Prioritize keys from financial_results if there are overlaps with market_solution
            # though typically market_solution contains dispatch and prices, financials contains monetary outcomes.

            # Ensure financial_results is not just an error message
            if "error" in financial_results:
                 return {
                    "error": "Financial calculation failed after successful dispatch.",
                    "details": financial_results["error"],
                    "market_solution_summary": {
                        "status": market_solution.get('status'),
                        "total_cost": market_solution.get('total_cost')
                    }
                }

            # Merging results: market_solution contains operational details and prices,
            # financial_results contains monetary outcomes.
            # A simple merge might be okay if keys are distinct, or structure them:
            return {
                "simulation_type": "traditional",
                "status": "success",
                "operational_results": market_solution,
                "financial_results": financial_results
            }
        else:
            return {
                "error": "Traditional simulation failed during market solving.",
                "details": market_solution.get('message', 'No details from solver.'),
                "status": market_solution.get('status', 'failure'),
                "market_solution_attempt": market_solution # Return whatever partial info solver gave
            }
    except Exception as e:
        import traceback
        print(f"Exception in run_traditional_simulation: {e}\n{traceback.format_exc()}")
        return {"error": "An unexpected error occurred in the traditional simulation engine.", "details": str(e)}
