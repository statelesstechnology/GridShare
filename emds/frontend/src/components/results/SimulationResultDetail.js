import React from 'react';
import GridDisplay from '../visualization/GridDisplay'; // Import GridDisplay

const detailStyles = {
  container: { padding: '20px', border: '1px solid #e0e0e0', borderRadius: '8px', backgroundColor: '#f9f9f9' },
  sectionTitle: { fontSize: '1.5em', color: '#333', marginTop: '20px', marginBottom: '10px', borderBottom: '2px solid #007bff', paddingBottom: '5px' },
  subSectionTitle: { fontSize: '1.2em', color: '#444', marginTop: '15px', marginBottom: '8px' },
  gridDisplayContainer: { height: '400px', marginBottom: '20px' }, // Ensure GridDisplay has a container with defined height
  table: { width: '100%', borderCollapse: 'collapse', marginTop: '10px', fontSize: '0.9em' },
  th: { backgroundColor: '#f0f0f0', border: '1px solid #ccc', padding: '8px', textAlign: 'left', fontWeight: 'bold' },
  td: { border: '1px solid #ccc', padding: '8px', textAlign: 'left' },
  error: { color: 'red', fontWeight: 'bold', padding: '10px', border: '1px solid red', borderRadius: '5px', backgroundColor: '#ffe0e0' },
  preFormatted: { whiteSpace: 'pre-wrap', wordWrap: 'break-word', backgroundColor: '#eee', padding: '10px', borderRadius: '5px', maxHeight: '300px', overflowY: 'auto' },
  summaryItem: { marginBottom: '8px', fontSize: '1em' }
};

function SimulationResultDetail({ resultData, scenarioData }) { // Added scenarioData prop
  if (!resultData) {
    return <p>No result data available.</p>;
  }

  // Destructure fields from resultData, providing defaults
  const {
    framework_type = 'N/A',
    simulation_timestamp,
    status = 'N/A',
    error_message,
    total_dispatch_cost,
    total_consumer_payment,
    total_generator_revenue,
    total_security_charges_collected,
    summary_results = {},
    detailed_generator_results = [],
    detailed_load_results = [],
    detailed_line_results = [],
    contingency_analysis_summary = {}
  } = resultData;

  const formatTimestamp = (ts) => ts ? new Date(ts).toLocaleString() : 'N/A';
  const formatNumber = (num, dp = 2) => (typeof num === 'number' ? num.toFixed(dp) : 'N/A');

  return (
    <div style={detailStyles.container}>
      <h2 style={detailStyles.sectionTitle}>Simulation Result Details</h2>

      {/* Grid Visualization */}
      {scenarioData && status === 'success' && ( // Only show grid if scenario and successful result data exist
        <>
          <div style={detailStyles.subSectionTitle}>Grid Visualization with Results</div>
          <div style={detailStyles.gridDisplayContainer}>
            <GridDisplay scenarioData={scenarioData} simulationResultData={resultData} />
          </div>
        </>
      )}

      {status === 'failure' && (
        <div style={detailStyles.error}>
          <strong>Simulation Failed:</strong> {error_message || 'No specific error message provided.'}
        </div>
      )}

      <div style={detailStyles.subSectionTitle}>Overall Summary</div>
      <p style={detailStyles.summaryItem}><strong>Framework:</strong> {framework_type}</p>
      <p style={detailStyles.summaryItem}><strong>Simulated At:</strong> {formatTimestamp(simulation_timestamp)}</p>
      <p style={detailStyles.summaryItem}><strong>Status:</strong> <span style={{ color: status === 'success' ? 'green' : 'red', fontWeight: 'bold' }}>{status}</span></p>

      {status === 'success' && (
        <>
          <p style={detailStyles.summaryItem}><strong>Total Dispatch Cost:</strong> ${formatNumber(total_dispatch_cost)}</p>
          <p style={detailStyles.summaryItem}><strong>Total Consumer Payment:</strong> ${formatNumber(total_consumer_payment)}</p>
          <p style={detailStyles.summaryItem}><strong>Total Generator Revenue:</strong> ${formatNumber(total_generator_revenue)}</p>
          {framework_type === 'causation' && (
            <p style={detailStyles.summaryItem}><strong>Total Security Charges Collected:</strong> ${formatNumber(total_security_charges_collected)}</p>
          )}

          {Object.keys(summary_results).length > 0 && (
            <>
              <div style={detailStyles.subSectionTitle}>System Metrics</div>
              <table style={detailStyles.table}>
                <thead>
                  <tr>
                    <th style={detailStyles.th}>Metric</th>
                    <th style={detailStyles.th}>Value</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(summary_results).map(([key, value]) => (
                    <tr key={key}>
                      <td style={detailStyles.td}>{key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</td>
                      <td style={detailStyles.td}>{typeof value === 'object' ? JSON.stringify(value) : formatNumber(value, typeof value === 'number' && !Number.isInteger(value) ? 2 : 0) }</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}

          {detailed_generator_results.length > 0 && (
            <>
              <div style={detailStyles.subSectionTitle}>Generator Results</div>
              <table style={detailStyles.table}>
                <thead>
                  <tr>
                    <th style={detailStyles.th}>ID</th>
                    <th style={detailStyles.th}>Bus</th>
                    <th style={detailStyles.th}>Power (MW)</th>
                    <th style={detailStyles.th}>R.Up (MW)</th>
                    <th style={detailStyles.th}>R.Down (MW)</th>
                    <th style={detailStyles.th}>LMP ($/MWh)</th>
                    <th style={detailStyles.th}>Profit ($)</th>
                    {framework_type === 'causation' && <th style={detailStyles.th}>Security Charge ($)</th>}
                  </tr>
                </thead>
                <tbody>
                  {detailed_generator_results.map((gen, index) => (
                    <tr key={gen.id || index}>
                      <td style={detailStyles.td}>{gen.id}</td>
                      <td style={detailStyles.td}>{gen.bus_id}</td>
                      <td style={detailStyles.td}>{formatNumber(gen.power_output_mw)}</td>
                      <td style={detailStyles.td}>{formatNumber(gen.reserve_up_mw)}</td>
                      <td style={detailStyles.td}>{formatNumber(gen.reserve_down_mw)}</td>
                      <td style={detailStyles.td}>{formatNumber(gen.lmp_at_bus_mwh)}</td>
                      <td style={detailStyles.td}>{formatNumber(gen.profit)}</td>
                      {framework_type === 'causation' && <td style={detailStyles.td}>{formatNumber(gen.security_charge)}</td>}
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}

          {detailed_load_results.length > 0 && (
            <>
              <div style={detailStyles.subSectionTitle}>Load Results</div>
              <table style={detailStyles.table}>
                <thead>
                  <tr>
                    <th style={detailStyles.th}>ID</th>
                    <th style={detailStyles.th}>Bus</th>
                    <th style={detailStyles.th}>Demand (MW)</th>
                    <th style={detailStyles.th}>LMP ($/MWh)</th>
                    <th style={detailStyles.th}>Payment ($)</th>
                  </tr>
                </thead>
                <tbody>
                  {detailed_load_results.map((load, index) => (
                    <tr key={load.id || index}>
                      <td style={detailStyles.td}>{load.id}</td>
                      <td style={detailStyles.td}>{load.bus_id}</td>
                      <td style={detailStyles.td}>{formatNumber(load.demand_mw)}</td>
                      <td style={detailStyles.td}>{formatNumber(load.lmp_at_bus_mwh)}</td>
                      <td style={detailStyles.td}>{formatNumber(load.payment_for_energy)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}

          {detailed_line_results.length > 0 && (
             <>
              <div style={detailStyles.subSectionTitle}>Line Flows</div>
              <table style={detailStyles.table}>
                <thead>
                  <tr>
                    <th style={detailStyles.th}>ID</th>
                    <th style={detailStyles.th}>From Bus</th>
                    <th style={detailStyles.th}>To Bus</th>
                    <th style={detailStyles.th}>Flow (MW)</th>
                    <th style={detailStyles.th}>Limit (MW)</th>
                    <th style={detailStyles.th}>Cong. Value ($)</th>
                  </tr>
                </thead>
                <tbody>
                  {detailed_line_results.map((line, index) => (
                    <tr key={line.id || index}>
                      <td style={detailStyles.td}>{line.id}</td>
                      <td style={detailStyles.td}>{line.from_bus}</td>
                      <td style={detailStyles.td}>{line.to_bus}</td>
                      <td style={detailStyles.td}>{formatNumber(line.flow_mw)}</td>
                      <td style={detailStyles.td}>{formatNumber(line.flow_limit_mw)}</td>
                      <td style={detailStyles.td}>{formatNumber(line.congestion_value_approx)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}

          {framework_type === 'causation' && Object.keys(contingency_analysis_summary).length > 0 && (
            <>
              <div style={detailStyles.subSectionTitle}>Contingency Analysis Summary</div>
              <pre style={detailStyles.preFormatted}>
                {JSON.stringify(contingency_analysis_summary, null, 2)}
              </pre>
            </>
          )}
        </>
      )}
    </div>
  );
}

export default SimulationResultDetail;
