-- Drop existing tables to allow re-running the script
DROP TABLE IF EXISTS simulation_results CASCADE;
DROP TABLE IF EXISTS scenarios CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- Function to update the updated_at column
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
   NEW.updated_at = NOW();
   RETURN NEW;
END;
$$ language 'plpgsql';

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    password_hash VARCHAR(128) NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Scenarios table
CREATE TABLE IF NOT EXISTS scenarios (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE, -- Remove user's scenarios if user is deleted
    name VARCHAR(100) NOT NULL,
    description TEXT, -- Optional: a brief description of the scenario
    grid_config JSONB,
    generator_data JSONB,
    load_data JSONB,
    transmission_data JSONB,
    contingency_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Trigger to update the updated_at column on scenarios table modification
CREATE TRIGGER update_scenarios_updated_at
BEFORE UPDATE ON scenarios
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- Simulation Results table
CREATE TABLE IF NOT EXISTS simulation_results (
    id SERIAL PRIMARY KEY,
    scenario_id INTEGER REFERENCES scenarios(id) ON DELETE CASCADE NOT NULL,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL, -- Keep results even if user is deleted, but unlink
    framework_type VARCHAR(50) NOT NULL, -- e.g., 'traditional', 'causation'
    simulation_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) NOT NULL, -- e.g., 'success', 'failure', 'partial'
    error_message TEXT, -- If status is 'failure'

    -- Key summary results (denormalized for easier querying, can be extensive)
    total_dispatch_cost NUMERIC,
    total_consumer_payment NUMERIC,
    total_generator_revenue NUMERIC,
    total_security_charges_collected NUMERIC, -- Specific to causation model

    -- Store more detailed results as JSONB for flexibility
    summary_results JSONB, -- For overall system metrics, prices (LMPs, reserve prices)
    detailed_generator_results JSONB, -- Array of objects: gen_id, power_mw, reserve_up_mw, reserve_down_mw, profit, energy_revenue, reserve_revenue, security_charge
    detailed_load_results JSONB, -- Array of objects: load_id, demand_mw, payment_energy
    detailed_line_results JSONB, -- Array of objects: line_id, flow_mw, lmp_from, lmp_to, congestion_value
    contingency_analysis_summary JSONB, -- Specific to causation: summary of violations and causers

    -- Optional: Store the input scenario snapshot used for this simulation,
    -- if scenarios can change and you need to reproduce results with exact inputs.
    -- scenario_snapshot JSONB,

    notes TEXT -- Any user or system notes about this specific simulation run
);

-- Indexes for faster querying of results
CREATE INDEX IF NOT EXISTS idx_simulation_results_scenario_id ON simulation_results(scenario_id);
CREATE INDEX IF NOT EXISTS idx_simulation_results_user_id ON simulation_results(user_id);
CREATE INDEX IF NOT EXISTS idx_simulation_results_framework_type ON simulation_results(framework_type);
CREATE INDEX IF NOT EXISTS idx_simulation_results_status ON simulation_results(status);


-- Comments on specific fields:
-- users.password_hash: Stores the hashed version of the user's password.
-- scenarios.user_id: Foreign key linking to the users table. Ensures scenarios are associated with a user.
-- ... (other comments from previous version are still valid) ...
-- simulation_results: Stores the output from running a simulation model on a specific scenario.
-- simulation_results.user_id: Denormalized for easier querying of all results by a user, even if they don't own the scenario (e.g. shared scenarios in future).
-- simulation_results.total_dispatch_cost etc: Key metrics promoted to top-level columns for easy access.
-- simulation_results.summary_results, .detailed_generator_results etc: JSONB fields to store complex, variable structure data from simulation outputs.
-- simulation_results.scenario_snapshot: Can be used if there's a need to archive the exact scenario input that produced the result, as the original scenario might be edited later.

-- Note on JSONB vs JSON: JSONB is used for its performance benefits (indexed, binary format).
-- The structures provided in comments are examples and can be extended as needed.
-- It's good practice to validate the JSONB structures within the application logic before insertion/update.
