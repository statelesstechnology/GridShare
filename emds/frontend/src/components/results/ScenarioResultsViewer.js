import React, { useState, useEffect, useCallback } from 'react';
import SimulationResultDetail from './SimulationResultDetail';
import ComparisonCharts from './ComparisonCharts'; // Import ComparisonCharts

const viewerStyles = {
  container: { padding: '20px' },
  button: { marginRight: '10px', padding: '10px 15px', backgroundColor: '#007bff', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', marginBottom: '10px' },
  backButton: { backgroundColor: '#6c757d' },
  list: { listStyle: 'none', padding: 0 },
  listItem: { border: '1px solid #eee', padding: '10px', marginBottom: '10px', borderRadius: '5px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap' },
  listItemInfo: { flexGrow: 1, minWidth: '200px' },
  listItemActions: { display: 'flex', gap: '10px', marginTop: '5px', flexWrap: 'wrap' }, // Allow actions to wrap
  viewDetailsButton: { padding: '8px 12px', backgroundColor: '#28a745', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '0.9em' },
  selectCompareButton: { padding: '8px 12px', backgroundColor: '#ffc107', color: 'black', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '0.9em' },
  loading: { fontStyle: 'italic', color: '#777', margin: '10px 0' },
  error: { color: 'red', fontWeight: 'bold', padding: '10px', border: '1px solid red', borderRadius: '5px', backgroundColor: '#ffe0e0', marginBottom: '10px' },
  noResults: { fontStyle: 'italic', color: '#555', marginTop: '15px' },
  comparisonSection: { marginTop: '20px', padding: '15px', border: '1px solid #007bff', borderRadius: '8px', backgroundColor: '#f0f8ff' },
  comparisonTitle: { fontSize: '1.4em', color: '#0056b3', marginBottom: '15px' },
  comparisonSlot: { marginBottom: '10px', padding: '8px', border: '1px dashed #ccc', borderRadius: '4px', backgroundColor: '#fff' },
  clearButton: { fontSize: '0.8em', padding: '4px 8px', backgroundColor: '#adb5bd', marginLeft: '10px'}
};

function ScenarioResultsViewer({ scenarioId, userId, token, onBackToScenarioList }) {
  const [currentScenarioFullData, setCurrentScenarioFullData] = useState(null); // For GridDisplay
  const [simulationRuns, setSimulationRuns] = useState([]);
  const [selectedResultDetail, setSelectedResultDetail] = useState(null);

  const [isLoadingList, setIsLoadingList] = useState(false);
  const [listError, setListError] = useState(null);

  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [detailError, setDetailError] = useState(null);

  // State for comparison
  const [compareTradResultId, setCompareTradResultId] = useState(null);
  const [compareCausResultId, setCompareCausResultId] = useState(null);
  const [compareTradResultDetails, setCompareTradResultDetails] = useState(null);
  const [compareCausResultDetails, setCompareCausResultDetails] = useState(null);
  const [showComparisonView, setShowComparisonView] = useState(false);
  const [isLoadingCompare, setIsLoadingCompare] = useState(false);


  // Fetch current scenario's full data (for GridDisplay)
  useEffect(() => {
    if (!scenarioId || !userId) return;
    const fetchScenarioDetails = async () => {
        // Not setting loading state here to avoid too many spinners, assume it's quick
        try {
            const headers = { 'X-User-ID': userId.toString() };
            const response = await fetch(`/api/scenarios/${scenarioId}`, { headers });
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(`Failed to fetch scenario details: ${response.status} ${errorData.error || response.statusText}`);
            }
            setCurrentScenarioFullData(await response.json());
        } catch (err) {
            setListError(prev => prev ? `${prev}\nFailed to fetch scenario details: ${err.message}` : `Failed to fetch scenario details: ${err.message}`);
            console.error("Error fetching scenario details:", err);
        }
    };
    fetchScenarioDetails();
  }, [scenarioId, userId, token]);


  const fetchResultDetailsCallback = useCallback(async (resultId, type) => {
    if (!resultId) return null;
    // Avoid re-fetching if already loaded for comparison
    if (type === 'traditional' && compareTradResultDetails && compareTradResultDetails.id === resultId) return compareTradResultDetails;
    if (type === 'causation' && compareCausResultDetails && compareCausResultDetails.id === resultId) return compareCausResultDetails;

    setIsLoadingCompare(true);
    setDetailError(null);
    try {
      const headers = { 'X-User-ID': userId.toString() };
      const response = await fetch(`/api/simulations/results/${resultId}`, { headers });
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(`Failed to fetch result details for ID ${resultId}: ${response.status} ${errorData.error || response.statusText}`);
      }
      const data = await response.json();
      if (type === 'traditional') setCompareTradResultDetails(data);
      else if (type === 'causation') setCompareCausResultDetails(data);
      return data;
    } catch (err) {
      setDetailError(err.message);
      console.error(`Error fetching details for ${resultId}:`, err);
      return null;
    } finally {
      setIsLoadingCompare(false);
    }
  }, [userId, token, compareTradResultDetails, compareCausResultDetails]); // Dependencies for useCallback


  useEffect(() => {
    if (!scenarioId || !userId) return;
    const fetchRuns = async () => {
      setIsLoadingList(true);
      setListError(null);
      setSelectedResultDetail(null);
      setCompareTradResultId(null); setCompareCausResultId(null);
      setCompareTradResultDetails(null); setCompareCausResultDetails(null);
      setShowComparisonView(false);

      try {
        const headers = { 'X-User-ID': userId.toString() };
        const response = await fetch(`/api/scenarios/${scenarioId}/results`, { headers });
        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(`Failed to fetch simulation runs: ${response.status} ${errorData.error || response.statusText}`);
        }
        setSimulationRuns(await response.json());
      } catch (err) {
        setListError(err.message);
      } finally {
        setIsLoadingList(false);
      }
    };
    fetchRuns();
  }, [scenarioId, userId, token]); // Main data fetching effect for runs

  const handleViewDetails = async (resultId) => {
    setShowComparisonView(false);
    setIsLoadingDetail(true);
    setDetailError(null);
    try {
      const headers = { 'X-User-ID': userId.toString() };
      const response = await fetch(`/api/simulations/results/${resultId}`, { headers });
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(`Failed to fetch result details: ${response.status} ${errorData.error || response.statusText}`);
      }
      setSelectedResultDetail(await response.json());
    } catch (err) {
      setDetailError(err.message);
    } finally {
      setIsLoadingDetail(false);
    }
  };

  const handleBackToRunList = () => {
    setSelectedResultDetail(null);
    setDetailError(null);
    setShowComparisonView(false);
  };

  const handleSelectForCompare = (run) => {
    if (run.framework_type === 'traditional') {
      setCompareTradResultId(run.id);
      fetchResultDetailsCallback(run.id, 'traditional');
    } else if (run.framework_type === 'causation') {
      setCompareCausResultId(run.id);
      fetchResultDetailsCallback(run.id, 'causation');
    }
  };

  const handleShowComparison = () => {
    if (compareTradResultDetails && compareCausResultDetails) {
      setShowComparisonView(true);
      setSelectedResultDetail(null);
    } else {
      alert("Please select one traditional and one causation result to compare. Details might still be loading if you just selected.");
    }
  };

  // Render logic
  if (isLoadingList) return <p style={viewerStyles.loading}>Loading simulation runs...</p>;
  if (listError) return (
    <div style={viewerStyles.container}>
      <p style={viewerStyles.error}>Error: {listError}</p>
      <button onClick={onBackToScenarioList} style={{...viewerStyles.button, ...viewerStyles.backButton}}>Back to Scenario List</button>
    </div>
  );

  if (showComparisonView) {
    return (
      <div style={viewerStyles.container}>
        <button onClick={() => { setShowComparisonView(false); setDetailError(null);}} style={{...viewerStyles.button, ...viewerStyles.backButton}}>Back to Simulation Runs</button>
        {isLoadingCompare && <p style={viewerStyles.loading}>Loading comparison data...</p>}
        {!isLoadingCompare && <ComparisonCharts traditionalResult={compareTradResultDetails} causationResult={compareCausResultDetails} />}
      </div>
    );
  }

  if (selectedResultDetail) {
    return (
      <div style={viewerStyles.container}>
        <button onClick={handleBackToRunList} style={{...viewerStyles.button, ...viewerStyles.backButton}}>Back to Simulation Runs</button>
        {isLoadingDetail && <p style={viewerStyles.loading}>Loading details...</p>}
        {detailError && <p style={viewerStyles.error}>Error loading details: {detailError}</p>}
        {!isLoadingDetail && !detailError &&
          <SimulationResultDetail
            resultData={selectedResultDetail}
            scenarioData={currentScenarioFullData} // Pass full scenario data here
          />}
      </div>
    );
  }

  return (
    <div style={viewerStyles.container}>
      <button onClick={onBackToScenarioList} style={{...viewerStyles.button, ...viewerStyles.backButton}}>Back to Scenario List</button>
      <h2>Simulation Runs for Scenario ID: {scenarioId}</h2>
      {!currentScenarioFullData && <p style={viewerStyles.loading}>Loading scenario base data...</p>}

      {detailError && <p style={viewerStyles.error}>{detailError}</p>}

      <div style={viewerStyles.comparisonSection}>
        <h3 style={viewerStyles.comparisonTitle}>Compare Results</h3>
        <div style={viewerStyles.comparisonSlot}>
          Traditional: {compareTradResultDetails ? `Run ${compareTradResultDetails.id} (Loaded)` : (compareTradResultId ? 'Loading...' : 'None selected')}
          {compareTradResultDetails && <button style={viewerStyles.clearButton} onClick={() => {setCompareTradResultId(null); setCompareTradResultDetails(null);}}>Clear</button>}
        </div>
        <div style={viewerStyles.comparisonSlot}>
          Causation: {compareCausResultDetails ? `Run ${compareCausResultDetails.id} (Loaded)` : (compareCausResultId ? 'Loading...' : 'None selected')}
          {compareCausResultDetails && <button style={viewerStyles.clearButton} onClick={() => {setCompareCausResultId(null); setCompareCausResultDetails(null);}}>Clear</button>}
        </div>
        <button onClick={handleShowComparison} style={viewerStyles.button} disabled={!compareTradResultDetails || !compareCausResultDetails || isLoadingCompare}>
          {isLoadingCompare ? 'Loading Data...' : 'Show Comparison Charts'}
        </button>
      </div>

      {simulationRuns.length === 0 && !isLoadingList ? (
        <p style={viewerStyles.noResults}>No simulation results found for this scenario.</p>
      ) : (
        <>
          <h3>Available Simulation Runs:</h3>
          <ul style={viewerStyles.list}>
            {simulationRuns.map(run => (
              <li key={run.id} style={viewerStyles.listItem}>
                <div style={viewerStyles.listItemInfo}>
                  <strong>ID: {run.id} | Framework:</strong> {run.framework_type} <br />
                  <strong>Timestamp:</strong> {new Date(run.simulation_timestamp).toLocaleString()} <br />
                  <strong>Status:</strong> <span style={{color: run.status === 'success' ? 'green' : 'red', fontWeight: 'bold'}}>{run.status}</span>
                  {run.status === 'failure' && <><br/><small style={{color:'grey'}}><i>Error: {run.error_message?.substring(0,100)||"Unknown"}...</i></small></>}
                </div>
                <div style={viewerStyles.listItemActions}>
                  <button onClick={() => handleViewDetails(run.id)} style={viewerStyles.viewDetailsButton} disabled={isLoadingDetail}>View Details</button>
                  {run.status === 'success' && (
                    <button
                      onClick={() => handleSelectForCompare(run)}
                      style={viewerStyles.selectCompareButton}
                      disabled={isLoadingCompare || (run.framework_type === 'traditional' && run.id === compareTradResultId) || (run.framework_type === 'causation' && run.id === compareCausResultId)}
                    >
                      { (run.framework_type === 'traditional' && run.id === compareTradResultId) || (run.framework_type === 'causation' && run.id === compareCausResultId)
                        ? 'Selected'
                        : `Select for Compare (${run.framework_type})`
                      }
                    </button>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}

export default ScenarioResultsViewer;
