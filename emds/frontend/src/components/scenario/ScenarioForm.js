import React, { useState, useEffect } from 'react';
// Basic styling, can be expanded in a dedicated CSS file
const formStyles = {
  sectionTitle: { marginTop: '20px', marginBottom: '10px', fontSize: '1.2em', fontWeight: 'bold' },
  inputGroup: { marginBottom: '10px', padding: '10px', border: '1px solid #eee', borderRadius: '5px' },
  inputField: { marginRight: '10px', marginBottom: '5px', padding: '5px', border: '1px solid #ccc', borderRadius: '3px' },
  button: { marginRight: '10px', padding: '8px 12px', backgroundColor: '#007bff', color: 'white', border: 'none', borderRadius: '3px', cursor: 'pointer' },
  removeButton: { padding: '5px 8px', backgroundColor: '#dc3545', color: 'white', border: 'none', borderRadius: '3px', cursor: 'pointer', marginLeft: '10px' },
  smallButton: { padding: '3px 6px', fontSize: '0.9em', marginLeft: '10px' }
};

const initialGridConfig = { num_buses: 0, num_generators: 0, num_loads: 0, num_transmission_lines: 0, buses: [] };
const initialContingencies = { generator_outages: [], line_outages: [] };

function ScenarioForm({ scenarioToEdit, onSave, onCancel }) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [gridConfig, setGridConfig] = useState(initialGridConfig);
  const [generators, setGenerators] = useState([]);
  const [loads, setLoads] = useState([]);
  const [lines, setLines] = useState([]);
  const [contingencies, setContingencies] = useState(initialContingencies);

  useEffect(() => {
    if (scenarioToEdit) {
      setName(scenarioToEdit.name || '');
      setDescription(scenarioToEdit.description || '');
      setGridConfig(scenarioToEdit.grid_config || initialGridConfig);
      setGenerators(scenarioToEdit.generator_data || []);
      setLoads(scenarioToEdit.load_data || []);
      setLines(scenarioToEdit.transmission_data || []);
      setContingencies(scenarioToEdit.contingency_data || initialContingencies);
    } else {
      // Reset to defaults for new form
      setName('');
      setDescription('');
      setGridConfig(initialGridConfig);
      setGenerators([]);
      setLoads([]);
      setLines([]);
      setContingencies(initialContingencies);
    }
  }, [scenarioToEdit]);

  const handleGridConfigChange = (e) => {
    const { name, value } = e.target;
    setGridConfig(prev => ({ ...prev, [name]: parseInt(value, 10) || 0 }));
  };

  // --- Generic Array Item Handlers ---
  const addItem = (setter, item) => setter(prev => [...prev, item]);
  const removeItem = (setter, index) => setter(prev => prev.filter((_, i) => i !== index));
  const handleItemChange = (setter, index, event) => {
    const { name, value, type, checked } = event.target;
    setter(prev => prev.map((item, i) =>
      i === index ? { ...item, [name]: type === 'checkbox' ? checked : (type === 'number' ? parseFloat(value) || 0 : value) } : item
    ));
  };

  // --- Specific Array Handlers ---
  // Generators
  const addGenerator = () => addItem(setGenerators, { id: `G${generators.length + 1}`, bus_id: 0, capacity_mw: 0, reserve_up_mw: 0, reserve_down_mw: 0, cost_energy_mwh: 0, cost_reserve_up_mw: 0, cost_reserve_down_mw: 0 });
  // Loads
  const addLoad = () => addItem(setLoads, { id: `L${loads.length + 1}`, bus_id: 0, demand_mw: 0, utility_mwh: 0, reserve_up_capacity_mw: 0, reserve_down_capacity_mw: 0, cost_reserve_up_mw: 0, cost_reserve_down_mw: 0 });
  // Lines
  const addLine = () => addItem(setLines, { id: `T${lines.length + 1}`, from_bus_id: 0, to_bus_id: 0, flow_limit_mw: 0, cost_mw_flow: 0 });
  // Contingencies
  const addGeneratorOutage = () => addItem(newSetter => setContingencies(prev => ({...prev, generator_outages: newSetter(prev.generator_outages)})), { generator_id: '', description: '' });
  const removeGeneratorOutage = (index) => setContingencies(prev => ({...prev, generator_outages: prev.generator_outages.filter((_, i) => i !== index)}));
  const handleGeneratorOutageChange = (index, event) => {
    const { name, value } = event.target;
    setContingencies(prev => ({
        ...prev,
        generator_outages: prev.generator_outages.map((item, i) =>
            i === index ? { ...item, [name]: value } : item
        )
    }));
  };

  const addLineOutage = () => addItem(newSetter => setContingencies(prev => ({...prev, line_outages: newSetter(prev.line_outages)})), { line_id: '', description: '' });
  const removeLineOutage = (index) => setContingencies(prev => ({...prev, line_outages: prev.line_outages.filter((_, i) => i !== index)}));
  const handleLineOutageChange = (index, event) => {
    const { name, value } = event.target;
    setContingencies(prev => ({
        ...prev,
        line_outages: prev.line_outages.map((item, i) =>
            i === index ? { ...item, [name]: value } : item
        )
    }));
  };


  const handleSubmit = (event) => {
    event.preventDefault();
    const scenarioData = {
      name,
      description,
      grid_config: gridConfig,
      generator_data: generators,
      load_data: loads,
      transmission_data: lines,
      contingency_data: contingencies,
    };
    if (scenarioToEdit && scenarioToEdit.id) {
        scenarioData.id = scenarioToEdit.id; // Include ID if editing
    }
    onSave(scenarioData);
  };

  return (
    <form onSubmit={handleSubmit} style={{padding: '20px', border: '1px solid #ccc', borderRadius: '8px'}}>
      <h3>{scenarioToEdit ? 'Edit Scenario' : 'Create New Scenario'}</h3>

      <div style={formStyles.inputGroup}>
        <label>Name:</label>
        <input type="text" style={formStyles.inputField} value={name} onChange={e => setName(e.target.value)} required />
      </div>
      <div style={formStyles.inputGroup}>
        <label>Description:</label>
        <textarea style={{...formStyles.inputField, width: '300px', minHeight: '60px'}} value={description} onChange={e => setDescription(e.target.value)} />
      </div>

      {/* Grid Configuration */}
      <div style={formStyles.sectionTitle}>Grid Configuration</div>
      <div style={formStyles.inputGroup}>
        <label>Number of Buses:</label>
        <input type="number" style={formStyles.inputField} name="num_buses" value={gridConfig.num_buses} onChange={handleGridConfigChange} />
        {/* Add other grid_config fields as needed e.g. num_generators, num_loads, num_transmission_lines */}
      </div>

      {/* Generators */}
      <div style={formStyles.sectionTitle}>Generators</div>
      {generators.map((gen, index) => (
        <div key={index} style={formStyles.inputGroup}>
          <strong>Generator {index + 1} (ID: {gen.id})</strong>
          <button type="button" style={formStyles.removeButton} onClick={() => removeItem(setGenerators, index)}>Remove</button>
          <br />
          <input type="text" style={formStyles.inputField} name="id" placeholder="ID (e.g. G1)" value={gen.id} onChange={e => handleItemChange(setGenerators, index, e)} />
          <input type="number" style={formStyles.inputField} name="bus_id" placeholder="Bus ID" value={gen.bus_id} onChange={e => handleItemChange(setGenerators, index, e)} />
          <input type="number" style={formStyles.inputField} name="capacity_mw" placeholder="Capacity (MW)" value={gen.capacity_mw} onChange={e => handleItemChange(setGenerators, index, e)} />
          <input type="number" style={formStyles.inputField} name="cost_energy_mwh" placeholder="Cost Energy (€/MWh)" value={gen.cost_energy_mwh} onChange={e => handleItemChange(setGenerators, index, e)} />
          {/* Add all other generator fields: reserve_up_mw, reserve_down_mw, cost_reserve_up_mw, cost_reserve_down_mw */}
        </div>
      ))}
      <button type="button" style={formStyles.button} onClick={addGenerator}>Add Generator</button>

      {/* Loads */}
      <div style={formStyles.sectionTitle}>Loads</div>
      {loads.map((load, index) => (
        <div key={index} style={formStyles.inputGroup}>
          <strong>Load {index + 1} (ID: {load.id})</strong>
          <button type="button" style={formStyles.removeButton} onClick={() => removeItem(setLoads, index)}>Remove</button>
          <br />
          <input type="text" style={formStyles.inputField} name="id" placeholder="ID (e.g. L1)" value={load.id} onChange={e => handleItemChange(setLoads, index, e)} />
          <input type="number" style={formStyles.inputField} name="bus_id" placeholder="Bus ID" value={load.bus_id} onChange={e => handleItemChange(setLoads, index, e)} />
          <input type="number" style={formStyles.inputField} name="demand_mw" placeholder="Demand (MW)" value={load.demand_mw} onChange={e => handleItemChange(setLoads, index, e)} />
          <input type="number" style={formStyles.inputField} name="utility_mwh" placeholder="Utility (€/MWh)" value={load.utility_mwh} onChange={e => handleItemChange(setLoads, index, e)} />
          {/* Add all other load fields */}
        </div>
      ))}
      <button type="button" style={formStyles.button} onClick={addLoad}>Add Load</button>

      {/* Transmission Lines */}
      <div style={formStyles.sectionTitle}>Transmission Lines</div>
      {lines.map((line, index) => (
        <div key={index} style={formStyles.inputGroup}>
          <strong>Line {index + 1} (ID: {line.id})</strong>
          <button type="button" style={formStyles.removeButton} onClick={() => removeItem(setLines, index)}>Remove</button>
          <br />
          <input type="text" style={formStyles.inputField} name="id" placeholder="ID (e.g. T1)" value={line.id} onChange={e => handleItemChange(setLines, index, e)} />
          <input type="number" style={formStyles.inputField} name="from_bus_id" placeholder="From Bus ID" value={line.from_bus_id} onChange={e => handleItemChange(setLines, index, e)} />
          <input type="number" style={formStyles.inputField} name="to_bus_id" placeholder="To Bus ID" value={line.to_bus_id} onChange={e => handleItemChange(setLines, index, e)} />
          <input type="number" style={formStyles.inputField} name="flow_limit_mw" placeholder="Flow Limit (MW)" value={line.flow_limit_mw} onChange={e => handleItemChange(setLines, index, e)} />
          {/* Add other line fields */}
        </div>
      ))}
      <button type="button" style={formStyles.button} onClick={addLine}>Add Line</button>

      {/* Contingencies */}
      <div style={formStyles.sectionTitle}>Contingencies</div>
      <div style={formStyles.inputGroup}>
        <strong>Generator Outages</strong>
        {contingencies.generator_outages.map((outage, index) => (
          <div key={index} style={{ marginTop: '5px' }}>
            <input type="text" style={formStyles.inputField} name="generator_id" placeholder="Generator ID (e.g. G1)" value={outage.generator_id} onChange={e => handleGeneratorOutageChange(index, e)} />
            <input type="text" style={formStyles.inputField} name="description" placeholder="Description" value={outage.description} onChange={e => handleGeneratorOutageChange(index, e)} />
            <button type="button" style={{...formStyles.removeButton, ...formStyles.smallButton}} onClick={() => removeGeneratorOutage(index)}>Remove</button>
          </div>
        ))}
        <button type="button" style={{...formStyles.button, ...formStyles.smallButton, marginTop: '5px'}} onClick={addGeneratorOutage}>Add Generator Outage</button>
      </div>
      <div style={formStyles.inputGroup}>
        <strong>Line Outages</strong>
        {contingencies.line_outages.map((outage, index) => (
          <div key={index} style={{ marginTop: '5px' }}>
            <input type="text" style={formStyles.inputField} name="line_id" placeholder="Line ID (e.g. T1)" value={outage.line_id} onChange={e => handleLineOutageChange(index, e)} />
            <input type="text" style={formStyles.inputField} name="description" placeholder="Description" value={outage.description} onChange={e => handleLineOutageChange(index, e)} />
            <button type="button" style={{...formStyles.removeButton, ...formStyles.smallButton}} onClick={() => removeLineOutage(index)}>Remove</button>
          </div>
        ))}
        <button type="button" style={{...formStyles.button, ...formStyles.smallButton, marginTop: '5px'}} onClick={addLineOutage}>Add Line Outage</button>
      </div>

      <div style={{marginTop: '30px'}}>
        <button type="submit" style={formStyles.button}>Save Scenario</button>
        <button type="button" style={{...formStyles.button, backgroundColor: '#6c757d'}} onClick={onCancel}>Cancel</button>
      </div>
    </form>
  );
}

export default ScenarioForm;
