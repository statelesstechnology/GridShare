import React, { useState, useEffect } from 'react';

// Basic styling, can be expanded
const listStyles = {
  container: { marginTop: '20px' },
  listItem: { border: '1px solid #ddd', padding: '15px', marginBottom: '10px', borderRadius: '5px', backgroundColor: '#f9f9f9', display: 'flex', justifyContent: 'space-between', alignItems: 'center' },
  itemContent: { flexGrow: 1 },
  itemName: { fontSize: '1.3em', marginBottom: '5px', color: '#333' },
  itemDetails: { fontSize: '0.9em', color: '#666', marginBottom: '10px' },
  buttonGroup: { display: 'flex', gap: '10px' }, // Use gap for spacing if supported, or marginRight on buttons
  button: { padding: '8px 12px', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '0.9em' },
  editButton: { backgroundColor: '#ffc107', color: 'black' },
  deleteButton: { backgroundColor: '#dc3545', color: 'white' },
  viewResultsButton: { backgroundColor: '#17a2b8', color: 'white' }, // New style for View Results
  loading: { fontStyle: 'italic', color: '#777' },
  error: { color: 'red', fontWeight: 'bold' },
  noScenarios: { fontStyle: 'italic', color: '#555', marginTop: '15px' }
};

function ScenarioList({ onEditScenario, onDeleteScenario, onViewResults, userId, token, refreshKey }) {
  const [scenarios, setScenarios] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!userId) {
      setScenarios([]); // Clear scenarios if no user ID
      return;
    }

    const fetchScenarios = async () => {
      setIsLoading(true);
      setError(null);
      try {
        // Use X-User-ID header as defined in backend setup for simulated auth
        const headers = {
          'Content-Type': 'application/json',
          'X-User-ID': userId.toString()
        };
        // If using a token for auth, it would be:
        // if (token) { headers['Authorization'] = `Bearer ${token}`; }

        const response = await fetch('/api/scenarios', { headers });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({})); // Try to parse error, default to empty obj
          throw new Error(`Failed to fetch scenarios: ${response.status} ${response.statusText}. ${errorData.error || ''}`);
        }
        const data = await response.json();
        setScenarios(data);
      } catch (err) {
        setError(err.message);
        console.error("Error fetching scenarios:", err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchScenarios();
  }, [userId, token, refreshKey]); // Re-fetch if userId, token, or refreshKey changes

  if (isLoading) {
    return <p style={listStyles.loading}>Loading scenarios...</p>;
  }

  if (error) {
    return <p style={listStyles.error}>Error loading scenarios: {error}</p>;
  }

  if (scenarios.length === 0) {
    return <p style={listStyles.noScenarios}>No scenarios found. Create one!</p>;
  }

  return (
    <div style={listStyles.container}>
      <h2>Your Scenarios</h2>
      {scenarios.map(scenario => (
        <div key={scenario.id} style={listStyles.listItem}>
          <h3 style={listStyles.itemName}>{scenario.name}</h3>
          {scenario.description && <p style={listStyles.itemDetails}>Description: {scenario.description}</p>}
          <p style={listStyles.itemDetails}>
            Created: {new Date(scenario.created_at).toLocaleString()} |
            Updated: {new Date(scenario.updated_at).toLocaleString()}
          </p>
          <div style={listStyles.itemContent}>
            <h3 style={listStyles.itemName}>{scenario.name}</h3>
            {scenario.description && <p style={listStyles.itemDetails}>Description: {scenario.description}</p>}
            <p style={listStyles.itemDetails}>
              Created: {new Date(scenario.created_at).toLocaleString()} |
              Updated: {new Date(scenario.updated_at).toLocaleString()}
            </p>
          </div>
          <div style={listStyles.buttonGroup}>
            <button
              onClick={() => onViewResults(scenario.id)}
              style={{...listStyles.button, ...listStyles.viewResultsButton}}
            >
              View Results
            </button>
            <button
              onClick={() => onEditScenario(scenario)}
              style={{...listStyles.button, ...listStyles.editButton}}
            >
              Edit
            </button>
            <button
              onClick={() => onDeleteScenario(scenario.id)}
              style={{...listStyles.button, ...listStyles.deleteButton}}
            >
              Delete
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}

export default ScenarioList;
