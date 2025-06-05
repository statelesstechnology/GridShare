import React, { useState, useEffect } from 'react';
import SignupForm from './components/SignupForm';
import LoginForm from './components/LoginForm';
import ScenarioForm from './components/scenario/ScenarioForm';
import ScenarioList from './components/scenario/ScenarioList';
import ScenarioResultsViewer from './components/results/ScenarioResultsViewer'; // Import Results Viewer
import './App.css';

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [userId, setUserId] = useState(null);
  const [token, setToken] = useState(null);

  // Scenario State
  const [showScenarioForm, setShowScenarioForm] = useState(false);
  const [editingScenario, setEditingScenario] = useState(null);
  const [refreshScenariosKey, setRefreshScenariosKey] = useState(0);

  // Results Viewer State
  const [viewingResultsForScenarioId, setViewingResultsForScenarioId] = useState(null);

  // --- Authentication ---
  useEffect(() => {
    const storedToken = localStorage.getItem('emds_token');
    const storedUserId = localStorage.getItem('emds_user_id');
    if (storedToken && storedUserId) {
      setIsLoggedIn(true);
      setUserId(storedUserId);
      setToken(storedToken);
    }
  }, []);

  const handleLoginSuccess = (apiToken, loggedInUserId, loggedInUsername) => {
    setIsLoggedIn(true);
    setUserId(loggedInUserId);
    setToken(apiToken);
    localStorage.setItem('emds_token', apiToken);
    localStorage.setItem('emds_user_id', loggedInUserId.toString());
    setRefreshScenariosKey(prevKey => prevKey + 1);
  };

  const handleLogout = () => {
    localStorage.removeItem('emds_token');
    localStorage.removeItem('emds_user_id');
    setIsLoggedIn(false);
    setUserId(null);
    setToken(null);
    setShowScenarioForm(false);
    setEditingScenario(null);
    setViewingResultsForScenarioId(null); // Clear results view on logout
    setRefreshScenariosKey(0);
  };

  // --- Scenario Management ---
  const handleOpenCreateScenarioForm = () => {
    setEditingScenario(null);
    setShowScenarioForm(true);
    setViewingResultsForScenarioId(null); // Hide results viewer
  };

  const handleEditScenario = (scenario) => {
    setEditingScenario(scenario);
    setShowScenarioForm(true);
    setViewingResultsForScenarioId(null); // Hide results viewer
  };

  const handleScenarioSave = async (scenarioData) => {
    const isUpdating = scenarioData.id;
    const url = isUpdating ? `/api/scenarios/${scenarioData.id}` : '/api/scenarios';
    const method = isUpdating ? 'PUT' : 'POST';

    try {
      const headers = { 'Content-Type': 'application/json', 'X-User-ID': userId.toString() };
      const response = await fetch(url, { method, headers, body: JSON.stringify(scenarioData) });
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(`Failed to ${isUpdating ? 'update' : 'create'} scenario: ${response.status} ${errorData.error || ''}`);
      }
      setShowScenarioForm(false);
      setEditingScenario(null);
      setRefreshScenariosKey(prevKey => prevKey + 1);
      alert(`Scenario successfully ${isUpdating ? 'updated' : 'created'}!`);
    } catch (error) {
      console.error("Error saving scenario:", error);
      alert(`Error saving scenario: ${error.message}`);
    }
  };

  const handleScenarioFormCancel = () => {
    setShowScenarioForm(false);
    setEditingScenario(null);
  };

  const handleDeleteScenario = async (scenarioId) => {
    if (!window.confirm("Are you sure you want to delete this scenario?")) return;
    try {
      const headers = { 'X-User-ID': userId.toString() };
      const response = await fetch(`/api/scenarios/${scenarioId}`, { method: 'DELETE', headers });
      if (!response.ok && response.status !== 204) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(`Failed to delete scenario: ${response.status} ${errorData.error || ''}`);
      }
      alert("Scenario deleted successfully!");
      setRefreshScenariosKey(prevKey => prevKey + 1);
    } catch (error) {
      console.error("Error deleting scenario:", error);
      alert(`Error deleting scenario: ${error.message}`);
    }
  };

  // --- Results Viewing ---
  const handleViewScenarioResults = (scenarioId) => {
    setViewingResultsForScenarioId(scenarioId);
    setShowScenarioForm(false); // Ensure scenario form is hidden
    setEditingScenario(null);
  };

  const handleBackToScenarioListFromResults = () => {
    setViewingResultsForScenarioId(null);
  };

  // --- Main Render Logic ---
  let currentView;
  if (!isLoggedIn) {
    currentView = (
      <div className="auth-forms-container">
        <SignupForm />
        <LoginForm onLoginSuccess={handleLoginSuccess} />
      </div>
    );
  } else if (viewingResultsForScenarioId) {
    currentView = (
      <ScenarioResultsViewer
        scenarioId={viewingResultsForScenarioId}
        userId={userId}
        token={token} // Pass if needed by viewer/detail components for direct API calls
        onBackToScenarioList={handleBackToScenarioListFromResults}
      />
    );
  } else if (showScenarioForm) {
    currentView = (
      <ScenarioForm
        scenarioToEdit={editingScenario}
        onSave={handleScenarioSave}
        onCancel={handleScenarioFormCancel}
      />
    );
  } else {
    currentView = (
      <>
        <button onClick={handleOpenCreateScenarioForm} className="button-primary" style={{ marginBottom: '20px' }}>
          Create New Scenario
        </button>
        <ScenarioList
          userId={userId}
          token={token}
          onEditScenario={handleEditScenario}
          onDeleteScenario={handleDeleteScenario}
          onViewResults={handleViewScenarioResults} // New prop for ScenarioList
          refreshKey={refreshScenariosKey}
        />
      </>
    );
  }

  return (
    <div className="App">
      <header className="App-header">
        <h1>Energy Market Dynamics Simulator</h1>
      </header>
      <main>
        {isLoggedIn && (
          <div className="user-greeting">
            <p>Welcome! (User ID: {userId})</p>
            <button onClick={handleLogout} className="button-logout">Logout</button>
            <hr className="app-hr" />
          </div>
        )}
        {currentView}
      </main>
    </div>
  );
}

export default App;
