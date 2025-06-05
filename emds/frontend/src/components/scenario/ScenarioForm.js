import React, { useState, useEffect, useMemo } from 'react';
import GridDisplay from '../visualization/GridDisplay'; // Import GridDisplay

// Basic styling, can be expanded in a dedicated CSS file
const formStyles = {
  formContainer: { display: 'flex', flexDirection: 'row', gap: '20px'},
  formFields: { flex: 1, padding: '20px', border: '1px solid #ccc', borderRadius: '8px', backgroundColor: '#f9f9f9' },
  visualizationArea: { flex: 1, padding: '20px', border: '1px solid #ddd', borderRadius: '8px', backgroundColor: '#fff' },
  sectionTitle: { marginTop: '20px', marginBottom: '10px', fontSize: '1.2em', fontWeight: 'bold', color: '#0056b3' },
  inputGroup: { marginBottom: '15px', padding: '10px', border: '1px solid #eee', borderRadius: '5px', backgroundColor: 'white' },
  inputField: { marginRight: '10px', marginBottom: '5px', padding: '8px', border: '1px solid #ccc', borderRadius: '4px', fontSize:'0.95em' },
  button: { marginRight: '10px', padding: '10px 15px', backgroundColor: '#007bff', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' },
  removeButton: { padding: '6px 10px', backgroundColor: '#dc3545', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', marginLeft: '10px', fontSize: '0.9em' },
  smallButton: { padding: '5px 8px', fontSize: '0.9em', marginLeft: '10px', marginTop: '5px' },
  actionButtons: {marginTop: '30px', display: 'flex', justifyContent: 'flex-end' }
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

  // This will hold the data structure for GridDisplay
  const currentScenarioStateForViz = useMemo(() => ({
    grid_config: gridConfig,
    generator_data: generators,
    load_data: loads,
    transmission_data: lines,
    // Contingencies are not typically visualized in this static way
  }), [gridConfig, generators, loads, lines]);


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
    const val = parseInt(value, 10)
    setGridConfig(prev => ({ ...prev, [name]: isNaN(val) ? 0 : val }));
  };

  // --- Generic Array Item Handlers ---
  const addItem = (setter, itemFactory) => setter(prev => [...prev, itemFactory(prev.length)]);
  const removeItem = (setter, index) => setter(prev => prev.filter((_, i) => i !== index));
  const handleItemChange = (setter, index, event) => {
    const { name, value, type, checked } = event.target;
    let parsedValue = value;
    if (type === 'number') {
        parsedValue = parseFloat(value);
        if (isNaN(parsedValue)) parsedValue = 0; // Default to 0 if parsing fails
    } else if (type === 'checkbox') {
        parsedValue = checked;
    }

    setter(prev => prev.map((item, i) =>
      i === index ? { ...item, [name]: parsedValue } : item
    ));
  };

  // --- Specific Array Handlers ---
  const addGenerator = () => addItem(setGenerators, (len) => ({ id: `G${len + 1}`, bus_id: 1, capacity_mw: 0, reserve_up_mw: 0, reserve_down_mw: 0, cost_energy_mwh: 0, cost_reserve_up_mw: 0, cost_reserve_down_mw: 0 }));
  const addLoad = () => addItem(setLoads, (len) => ({ id: `L${len + 1}`, bus_id: 1, demand_mw: 0, utility_mwh: 0, reserve_up_capacity_mw: 0, reserve_down_capacity_mw: 0, cost_reserve_up_mw: 0, cost_reserve_down_mw: 0 }));
  const addLine = () => addItem(setLines, (len) => ({ id: `T${len + 1}`, from_bus_id: 1, to_bus_id: 2, flow_limit_mw: 0, cost_mw_flow: 0 }));

  const addGeneratorOutage = () => setContingencies(prev => ({...prev, generator_outages: [...prev.generator_outages, {generator_id: '', description: ''}]}));
  const removeGeneratorOutage = (index) => setContingencies(prev => ({...prev, generator_outages: prev.generator_outages.filter((_, i) => i !== index)}));
  const handleGeneratorOutageChange = (index, event) => {
    const { name, value } = event.target;
    setContingencies(prev => ({ ...prev, generator_outages: prev.generator_outages.map((item, i) => i === index ? { ...item, [name]: value } : item) }));
  };

  const addLineOutage = () => setContingencies(prev => ({...prev, line_outages: [...prev.line_outages, {line_id: '', description: ''}]}));
  const removeLineOutage = (index) => setContingencies(prev => ({...prev, line_outages: prev.line_outages.filter((_, i) => i !== index)}));
  const handleLineOutageChange = (index, event) => {
    const { name, value } = event.target;
    setContingencies(prev => ({ ...prev, line_outages: prev.line_outages.map((item, i) => i === index ? { ...item, [name]: value } : item) }));
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
        scenarioData.id = scenarioToEdit.id;
    }
    onSave(scenarioData);
  };

  return (
    <div style={formStyles.formContainer}>
      <form onSubmit={handleSubmit} style={formStyles.formFields}>
        <h3>{scenarioToEdit ? 'Edit Scenario' : 'Create New Scenario'}</h3>

        <div style={formStyles.inputGroup}>
          <label>Name:</label>
          <input type="text" style={formStyles.inputField} value={name} onChange={e => setName(e.target.value)} required />
        </div>
        <div style={formStyles.inputGroup}>
          <label>Description:</label>
          <textarea style={{...formStyles.inputField, width: 'calc(100% - 20px)', minHeight: '60px'}} value={description} onChange={e => setDescription(e.target.value)} />
        </div>

        <div style={formStyles.sectionTitle}>Grid Configuration</div>
        <div style={formStyles.inputGroup}>
          <label>Number of Buses:</label>
          <input type="number" style={formStyles.inputField} name="num_buses" value={gridConfig.num_buses} onChange={handleGridConfigChange} min="0"/>
        </div>

        <div style={formStyles.sectionTitle}>Generators</div>
        {generators.map((gen, index) => (
          <div key={`gen-${index}`} style={formStyles.inputGroup}>
            <strong>Generator {index + 1} (ID: {gen.id})</strong>
            <button type="button" style={formStyles.removeButton} onClick={() => removeItem(setGenerators, index)}>Remove</button> <br />
            <input type="text" style={formStyles.inputField} name="id" placeholder="ID (e.g. G1)" value={gen.id} onChange={e => handleItemChange(setGenerators, index, e)} />
            <input type="number" style={formStyles.inputField} name="bus_id" placeholder="Bus ID" value={gen.bus_id} onChange={e => handleItemChange(setGenerators, index, e)} min="1" max={gridConfig.num_buses > 0 ? gridConfig.num_buses : undefined}/>
            <input type="number" style={formStyles.inputField} name="capacity_mw" placeholder="Capacity (MW)" value={gen.capacity_mw} onChange={e => handleItemChange(setGenerators, index, e)} min="0"/>
            <input type="number" style={formStyles.inputField} name="cost_energy_mwh" placeholder="Cost Energy (€/MWh)" value={gen.cost_energy_mwh} onChange={e => handleItemChange(setGenerators, index, e)} min="0"/>
            {/* TODO: Add other generator fields like reserves */}
          </div>
        ))}
        <button type="button" style={formStyles.button} onClick={addGenerator}>Add Generator</button>

        <div style={formStyles.sectionTitle}>Loads</div>
        {loads.map((load, index) => (
          <div key={`load-${index}`} style={formStyles.inputGroup}>
            <strong>Load {index + 1} (ID: {load.id})</strong>
            <button type="button" style={formStyles.removeButton} onClick={() => removeItem(setLoads, index)}>Remove</button> <br />
            <input type="text" style={formStyles.inputField} name="id" placeholder="ID (e.g. L1)" value={load.id} onChange={e => handleItemChange(setLoads, index, e)} />
            <input type="number" style={formStyles.inputField} name="bus_id" placeholder="Bus ID" value={load.bus_id} onChange={e => handleItemChange(setLoads, index, e)} min="1" max={gridConfig.num_buses > 0 ? gridConfig.num_buses : undefined}/>
            <input type="number" style={formStyles.inputField} name="demand_mw" placeholder="Demand (MW)" value={load.demand_mw} onChange={e => handleItemChange(setLoads, index, e)} min="0"/>
            {/* TODO: Add other load fields */}
          </div>
        ))}
        <button type="button" style={formStyles.button} onClick={addLoad}>Add Load</button>

        <div style={formStyles.sectionTitle}>Transmission Lines</div>
        {lines.map((line, index) => (
          <div key={`line-${index}`} style={formStyles.inputGroup}>
            <strong>Line {index + 1} (ID: {line.id})</strong>
            <button type="button" style={formStyles.removeButton} onClick={() => removeItem(setLines, index)}>Remove</button> <br />
            <input type="text" style={formStyles.inputField} name="id" placeholder="ID (e.g. T1)" value={line.id} onChange={e => handleItemChange(setLines, index, e)} />
            <input type="number" style={formStyles.inputField} name="from_bus_id" placeholder="From Bus ID" value={line.from_bus_id} onChange={e => handleItemChange(setLines, index, e)} min="1" max={gridConfig.num_buses > 0 ? gridConfig.num_buses : undefined}/>
            <input type="number" style={formStyles.inputField} name="to_bus_id" placeholder="To Bus ID" value={line.to_bus_id} onChange={e => handleItemChange(setLines, index, e)} min="1" max={gridConfig.num_buses > 0 ? gridConfig.num_buses : undefined}/>
            <input type="number" style={formStyles.inputField} name="flow_limit_mw" placeholder="Flow Limit (MW)" value={line.flow_limit_mw} onChange={e => handleItemChange(setLines, index, e)} min="0"/>
          </div>
        ))}
        <button type="button" style={formStyles.button} onClick={addLine}>Add Line</button>

        <div style={formStyles.sectionTitle}>Contingencies</div>
        <div style={formStyles.inputGroup}>
          <strong>Generator Outages</strong>
          {contingencies.generator_outages.map((outage, index) => (
            <div key={`gen-outage-${index}`} style={{ marginTop: '5px' }}>
              <input type="text" style={formStyles.inputField} name="generator_id" placeholder="Generator ID (e.g. G1)" value={outage.generator_id} onChange={e => handleGeneratorOutageChange(index, e)} />
              <input type="text" style={{...formStyles.inputField, width: '40%'}} name="description" placeholder="Description" value={outage.description} onChange={e => handleGeneratorOutageChange(index, e)} />
              <button type="button" style={{...formStyles.removeButton, ...formStyles.smallButton}} onClick={() => removeGeneratorOutage(index)}>Remove</button>
            </div>
          ))}
          <button type="button" style={{...formStyles.button, ...formStyles.smallButton}} onClick={addGeneratorOutage}>Add Generator Outage</button>
        </div>
        <div style={formStyles.inputGroup}>
          <strong>Line Outages</strong>
          {contingencies.line_outages.map((outage, index) => (
            <div key={`line-outage-${index}`} style={{ marginTop: '5px' }}>
              <input type="text" style={formStyles.inputField} name="line_id" placeholder="Line ID (e.g. T1)" value={outage.line_id} onChange={e => handleLineOutageChange(index, e)} />
              <input type="text" style={{...formStyles.inputField, width: '40%'}} name="description" placeholder="Description" value={outage.description} onChange={e => handleLineOutageChange(index, e)} />
              <button type="button" style={{...formStyles.removeButton, ...formStyles.smallButton}} onClick={() => removeLineOutage(index)}>Remove</button>
            </div>
          ))}
          <button type="button" style={{...formStyles.button, ...formStyles.smallButton}} onClick={addLineOutage}>Add Line Outage</button>
        </div>

        <div style={formStyles.actionButtons}>
          <button type="button" style={{...formStyles.button, backgroundColor: '#6c757d'}} onClick={onCancel}>Cancel</button>
          <button type="submit" style={formStyles.button}>Save Scenario</button>
        </div>
      </form>
      <div style={formStyles.visualizationArea}>
        <h4 style={{textAlign: 'center', marginTop: 0, color: '#0056b3'}}>Grid Visualization</h4>
        { (gridConfig.num_buses > 0 || generators.length > 0 || loads.length > 0 || lines.length > 0) ? (
            <GridDisplay scenarioData={currentScenarioStateForViz} />
          ) : (
            <p style={{textAlign: 'center', color: '#777'}}>Enter grid data to see visualization.</p>
          )
        }
      </div>
    </div>
  );
}

export default ScenarioForm;
