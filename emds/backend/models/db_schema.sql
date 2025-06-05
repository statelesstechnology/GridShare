-- Drop existing tables to allow re-running the script
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

    -- Configuration for the grid structure
    -- {
    --     "num_buses": 0, // Integer: Total number of buses in the system
    --     "num_generators": 0, // Integer: Total number of generators
    --     "num_loads": 0, // Integer: Total number of loads
    --     "num_transmission_lines": 0, // Integer: Total number of transmission lines
    --     "buses": [ // Array (Optional): Explicit bus definitions if needed beyond just numbers
    --         // { "id": 1, "name": "Bus A", "voltage_kv": 230 }
    --     ]
    -- }
    grid_config JSONB,

    -- Data for generators (array of objects)
    -- [
    --     {
    --         "id": "G1", // String: User-defined unique identifier for the generator
    --         "bus_id": 1, // Integer: ID of the bus this generator is connected to
    --         "capacity_mw": 100, // Number: Maximum power output (\overline{G_i})
    --         "reserve_up_mw": 20, // Number: Upward reserve capacity (\overline{R_i^{g,up}})
    --         "reserve_down_mw": 15, // Number: Downward reserve capacity (\overline{R_i^{g,dn}})
    --         "cost_energy_mwh": 50, // Number: Cost of energy production (c_i)
    --         "cost_reserve_up_mw": 10, // Number: Cost of providing upward reserve (q_i^{g,up})
    --         "cost_reserve_down_mw": 8, // Number: Cost of providing downward reserve (q_i^{g,dn})
    --         "ramp_rate_up_mw_per_min": 10, // Number (Optional): Maximum ramp-up rate
    --         "ramp_rate_down_mw_per_min": 10, // Number (Optional): Maximum ramp-down rate
    --         "min_uptime_hours": 4, // Number (Optional): Minimum time generator must stay online
    --         "min_downtime_hours": 2 // Number (Optional): Minimum time generator must stay offline
    --     }
    -- ]
    generator_data JSONB,

    -- Data for loads (array of objects)
    -- [
    --     {
    --         "id": "L1", // String: User-defined unique identifier for the load
    --         "bus_id": 1, // Integer: ID of the bus this load is connected to
    --         "demand_mw": 80, // Number: Power demand (d_j)
    --         "utility_mwh": 200, // Number: Utility if demand is met (w_j)
    --         "reserve_up_capacity_mw": 10, // Number: Demand reduction capacity (\overline{R_j^{d,up}})
    --         "reserve_down_capacity_mw": 5, // Number: Load increase capacity (\overline{R_j^{d,dn}})
    --         "cost_reserve_up_mw": 5, // Number: Cost for reducing demand (q_j^{d,up})
    --         "cost_reserve_down_mw": 3, // Number: Cost for increasing demand (q_j^{d,dn})
    --         "is_interruptible": false // Boolean (Optional): Whether the load can be shed
    --     }
    -- ]
    load_data JSONB,

    -- Data for transmission lines (array of objects)
    -- [
    --     {
    --         "id": "T1", // String: User-defined unique identifier for the line
    --         "from_bus_id": 1, // Integer: ID of the starting bus
    --         "to_bus_id": 2, // Integer: ID of the ending bus
    --         "flow_limit_mw": 120, // Number: Maximum power flow limit (F_l)
    --         "reactance_pu": 0.05, // Number (Optional): Per-unit reactance (for DC power flow)
    --         "resistance_pu": 0.01, // Number (Optional): Per-unit resistance
    --         "cost_mw_flow": 2 // Number (Optional): Associated cost per MW flow (not in original paper, for flexibility)
    --     }
    -- ]
    transmission_data JSONB,

    -- Data for contingencies (object with arrays)
    -- {
    --     "generator_outages": [ // Array: List of generator outage events
    --         {
    --           "generator_id": "G1", // String: ID of the generator that is out
    --           "description": "Scheduled maintenance for Generator G1" // String (Optional)
    --         }
    --     ],
    --     "line_outages": [ // Array: List of transmission line outage events
    --         {
    --           "line_id": "T1", // String: ID of the transmission line that is out
    --           "description": "Line T1 out due to fault" // String (Optional)
    --         }
    --     ]
    -- }
    contingency_data JSONB,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Trigger to update the updated_at column on scenarios table modification
CREATE TRIGGER update_scenarios_updated_at
BEFORE UPDATE ON scenarios
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- Comments on specific fields:
-- users.password_hash: Stores the hashed version of the user's password.
-- scenarios.user_id: Foreign key linking to the users table. Ensures scenarios are associated with a user.
-- scenarios.name: User-defined name for the scenario (e.g., "Peak Load Summer Day").
-- scenarios.description: A more detailed text field for the user to describe the scenario.
-- scenarios.grid_config: Defines the basic topology of the power grid.
-- scenarios.generator_data: Contains an array of objects, each detailing a generator's parameters.
-- scenarios.load_data: Contains an array of objects, each detailing a load's parameters.
-- scenarios.transmission_data: Contains an array of objects, each detailing a transmission line's parameters.
-- scenarios.contingency_data: Defines outage events (e.g., generator or line outages) for N-1 analysis.
-- scenarios.created_at: Timestamp of when the scenario was created.
-- scenarios.updated_at: Timestamp of the last update to the scenario. Updated automatically by a trigger.

-- Note on JSONB vs JSON: JSONB is used for its performance benefits (indexed, binary format).
-- The structures provided in comments are examples and can be extended as needed.
-- It's good practice to validate the JSONB structures within the application logic before insertion/update.
