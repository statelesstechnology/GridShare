import React, { useState, useEffect } from 'react';
import SignupForm from './components/SignupForm';
import LoginForm from './components/LoginForm';
import ScenarioForm from './components/scenario/ScenarioForm';
import ScenarioList from './components/scenario/ScenarioList'; // Import ScenarioList
import './App.css';

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [userId, setUserId] = useState(null);
  const [token, setToken] = useState(null); // Store token if needed for API calls beyond X-User-ID

  // Scenario State
  const [showScenarioForm, setShowScenarioForm] = useState(false);
  const [editingScenario, setEditingScenario] = useState(null);
  const [refreshScenariosKey, setRefreshScenariosKey] = useState(0); // Key to trigger list refresh

  // --- Authentication ---
  useEffect(() => {
    const storedToken = localStorage.getItem('emds_token');
    const storedUserId = localStorage.getItem('emds_user_id');
    if (storedToken && storedUserId) {
      setIsLoggedIn(true);
      setUserId(storedUserId);
      setToken(storedToken);
      // In a real app, verify token with backend here
    }
  }, []);

  const handleLoginSuccess = (apiToken, loggedInUserId, loggedInUsername) => {
    setIsLoggedIn(true);
    setUserId(loggedInUserId);
    setToken(apiToken); // Store the token
    localStorage.setItem('emds_token', apiToken); // Persist token
    localStorage.setItem('emds_user_id', loggedInUserId.toString()); // Persist userId
    // localStorage.setItem('emds_username', loggedInUsername); // Persist username if needed
    console.log("Login successful. UserID:", loggedInUserId, "Token:", apiToken);
    setRefreshScenariosKey(prevKey => prevKey + 1); // Refresh scenario list on login
  };

  const handleLogout = () => {
    localStorage.removeItem('emds_token');
    localStorage.removeItem('emds_user_id');
    // localStorage.removeItem('emds_username');
    setIsLoggedIn(false);
    setUserId(null);
    setToken(null);
    setShowScenarioForm(false);
    setEditingScenario(null);
    setRefreshScenariosKey(0); // Reset refresh key
    console.log("User logged out.");
  };

  // --- Scenario Management ---
  const handleOpenCreateScenarioForm = () => {
    setEditingScenario(null);
    setShowScenarioForm(true);
  };

  const handleEditScenario = (scenario) => {
    setEditingScenario(scenario);
    setShowScenarioForm(true);
  };

  const handleScenarioSave = async (scenarioData) => {
    const isUpdating = scenarioData.id; // If ID exists, we are updating
    const url = isUpdating ? `/api/scenarios/${scenarioData.id}` : '/api/scenarios';
    const method = isUpdating ? 'PUT' : 'POST';

    try {
      const headers = {
        'Content-Type': 'application/json',
        'X-User-ID': userId.toString() // Assuming backend uses this for auth
        // If using Bearer token: 'Authorization': `Bearer ${token}`
      };

      const response = await fetch(url, {
        method: method,
        headers: headers,
        body: JSON.stringify(scenarioData),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(`Failed to ${isUpdating ? 'update' : 'create'} scenario: ${response.status} ${errorData.error || ''}`);
      }

      const savedScenario = await response.json();
      console.log(isUpdating ? "Scenario updated:" : "Scenario created:", savedScenario);
      setShowScenarioForm(false);
      setEditingScenario(null);
      setRefreshScenariosKey(prevKey => prevKey + 1); // Trigger list refresh
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
    if (!window.confirm("Are you sure you want to delete this scenario?")) {
      return;
    }

    try {
      const headers = {
        'X-User-ID': userId.toString()
        // If using Bearer token: 'Authorization': `Bearer ${token}`
      };

      const response = await fetch(`/api/scenarios/${scenarioId}`, {
        method: 'DELETE',
        headers: headers,
      });

      if (!response.ok) {
        // For 204 No Content, response.json() will fail. Check status first.
        if (response.status === 204) {
             // Handled below
        } else {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(`Failed to delete scenario: ${response.status} ${errorData.error || ''}`);
        }
      }

      // Handle 204 No Content specifically for DELETE success
      if (response.status === 204) {
        console.log("Scenario deleted successfully, ID:", scenarioId);
        alert("Scenario deleted successfully!");
      } else {
        // This part might not be reached if error is thrown above, but good for robustness
        const result = await response.json().catch(() => ({ message: "Deleted successfully" }));
        console.log("Scenario deleted:", result);
        alert(result.message || "Scenario deleted successfully!");
      }

      setRefreshScenariosKey(prevKey => prevKey + 1); // Trigger list refresh
    } catch (error) {
      console.error("Error deleting scenario:", error);
      alert(`Error deleting scenario: ${error.message}`);
    }
  };


  return (
    <div className="App">
      <header className="App-header">
        <h1>Energy Market Dynamics Simulator</h1>
      </header>
      <main>
        {!isLoggedIn ? (
          <div className="auth-forms-container">
            <SignupForm />
            <LoginForm onLoginSuccess={handleLoginSuccess} />
          </div>
        ) : (
          <div>
            <div className="user-greeting">
              <p>Welcome! You are logged in. (User ID: {userId})</p>
              <button onClick={handleLogout} className="button-logout">Logout</button>
            </div>
            <hr className="app-hr" />

            {showScenarioForm ? (
              <ScenarioForm
                scenarioToEdit={editingScenario}
                onSave={handleScenarioSave}
                onCancel={handleScenarioFormCancel}
              />
            ) : (
              <>
                <button onClick={handleOpenCreateScenarioForm} className="button-primary" style={{ marginBottom: '20px' }}>
                  Create New Scenario
                </button>
                <ScenarioList
                  userId={userId}
                  token={token} // Pass token if ScenarioList needs it for auth (currently uses X-User-ID)
                  onEditScenario={handleEditScenario}
                  onDeleteScenario={handleDeleteScenario}
                  refreshKey={refreshScenariosKey} // Pass the key here
                />
              </>
            )}
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
