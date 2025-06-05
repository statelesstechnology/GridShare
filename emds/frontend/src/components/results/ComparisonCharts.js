import React from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, LabelList
} from 'recharts';

const chartStyles = {
  chartContainer: { marginBottom: '30px', padding: '20px', border: '1px solid #eee', borderRadius: '8px', backgroundColor: '#fff' },
  chartTitle: { fontSize: '1.3em', color: '#333', marginBottom: '20px', textAlign: 'center' },
};

const formatNumber = (num, dp = 0) => (typeof num === 'number' ? num.toFixed(dp) : 'N/A');

function ComparisonCharts({ traditionalResult, causationResult }) {
  if (!traditionalResult || !causationResult) {
    return <p>Please select both a traditional and a causation simulation result to compare.</p>;
  }

  // --- Data Preparation ---

  // 1. Overall System Metrics
  const tradSysSummary = traditionalResult.financial_results?.system_summary || {};
  // For causation, financial results are nested under final_causation_financials.system_summary
  const causSysSummary = causationResult.final_causation_financials?.system_summary || {};

  const overallData = [
    {
      name: 'Dispatch Cost',
      Traditional: parseFloat(tradSysSummary.total_dispatch_cost) || 0,
      // Causation base dispatch cost is in base_case_dispatch_solution.total_cost
      Causation: parseFloat(causationResult.base_case_dispatch_solution?.total_cost) || 0,
    },
    {
      name: 'Gen Revenue',
      Traditional: parseFloat(tradSysSummary.total_generator_revenue) || 0,
      Causation: parseFloat(causSysSummary.total_generator_revenue) || 0,
    },
    {
      name: 'Consumer Payment',
      Traditional: parseFloat(tradSysSummary.total_consumer_payment_for_energy) || 0,
      Causation: parseFloat(causSysSummary.total_consumer_payment_for_energy) || 0,
    },
    {
      name: 'Security Charges',
      Traditional: 0, // No security charges in traditional
      Causation: parseFloat(causSysSummary.total_security_charges_collected) || 0,
    },
  ];

  // 2. Generator Profits
  const tradGenDetails = traditionalResult.financial_results?.generator_details || [];
  const causGenDetails = causationResult.final_causation_financials?.generator_details || [];

  const generatorIds = new Set([...tradGenDetails.map(g => g.id), ...causGenDetails.map(g => g.id)]);

  const generatorProfitData = Array.from(generatorIds).map(id => {
    const tradGen = tradGenDetails.find(g => g.id === id);
    const causGen = causGenDetails.find(g => g.id === id);
    return {
      name: id,
      Traditional_Profit: parseFloat(tradGen?.profit) || 0,
      Causation_Profit: parseFloat(causGen?.profit) || 0,
      Traditional_SecCharge: 0, // For labeling if needed, though profit already includes it for causation
      Causation_SecCharge: parseFloat(causGen?.security_charge) || 0,
    };
  });

  // 3. Load Payments
  const tradLoadDetails = traditionalResult.financial_results?.load_details || [];
  // For causation, load details are from the base case traditional financials
  const causLoadDetails = causationResult.traditional_financials_for_base_case?.load_details || [];

  const loadIds = new Set([...tradLoadDetails.map(l => l.id), ...causLoadDetails.map(l => l.id)]);

  const loadPaymentData = Array.from(loadIds).map(id => {
    const tradLoad = tradLoadDetails.find(l => l.id === id);
    const causLoad = causLoadDetails.find(l => l.id === id);
    return {
      name: id,
      Traditional_Payment: parseFloat(tradLoad?.payment_for_energy) || 0,
      Causation_Payment: parseFloat(causLoad?.payment_for_energy) || 0, // Assuming base LMP for payment
    };
  });


  return (
    <div>
      <h2 style={{textAlign: 'center', color: '#0056b3', marginBottom: '30px'}}>Results Comparison</h2>

      {/* Overall System Metrics Chart */}
      <div style={chartStyles.chartContainer}>
        <h3 style={chartStyles.chartTitle}>Overall System Metrics</h3>
        <ResponsiveContainer width="100%" height={350}>
          <BarChart data={overallData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" />
            <YAxis />
            <Tooltip formatter={(value) => formatNumber(value, 2)}/>
            <Legend />
            <Bar dataKey="Traditional" fill="#8884d8" radius={[4, 4, 0, 0]}>
                <LabelList dataKey="Traditional" position="top" formatter={(value) => formatNumber(value,0)} />
            </Bar>
            <Bar dataKey="Causation" fill="#82ca9d" radius={[4, 4, 0, 0]}>
                <LabelList dataKey="Causation" position="top" formatter={(value) => formatNumber(value,0)} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Generator Profits Chart */}
      <div style={chartStyles.chartContainer}>
        <h3 style={chartStyles.chartTitle}>Generator Profits</h3>
        <ResponsiveContainer width="100%" height={350}>
          <BarChart data={generatorProfitData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" />
            <YAxis label={{ value: 'Profit ($)', angle: -90, position: 'insideLeft' }} />
            <Tooltip formatter={(value) => formatNumber(value, 2)}/>
            <Legend />
            <Bar dataKey="Traditional_Profit" name="Traditional Profit" fill="#8884d8" radius={[4, 4, 0, 0]}>
                <LabelList dataKey="Traditional_Profit" position="top" formatter={(value) => formatNumber(value,0)} />
            </Bar>
            <Bar dataKey="Causation_Profit" name="Causation Profit (after Sec. Charges)" fill="#82ca9d" radius={[4, 4, 0, 0]}>
                <LabelList dataKey="Causation_Profit" position="top" formatter={(value) => formatNumber(value,0)} />
            </Bar>
             <Bar dataKey="Causation_SecCharge" name="Causation Security Charge" fill="#ffc658" stackId="causation" radius={[4, 4, 0, 0]}>
                 <LabelList dataKey="Causation_SecCharge" position="center" formatter={(value) => value > 0 ? formatNumber(value,0) : ''} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Load Payments Chart */}
      <div style={chartStyles.chartContainer}>
        <h3 style={chartStyles.chartTitle}>Load Payments</h3>
        <ResponsiveContainer width="100%" height={350}>
          <BarChart data={loadPaymentData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" />
            <YAxis label={{ value: 'Payment ($)', angle: -90, position: 'insideLeft' }}/>
            <Tooltip formatter={(value) => formatNumber(value, 2)}/>
            <Legend />
            <Bar dataKey="Traditional_Payment" name="Traditional Payment" fill="#8884d8" radius={[4, 4, 0, 0]}>
                <LabelList dataKey="Traditional_Payment" position="top" formatter={(value) => formatNumber(value,0)} />
            </Bar>
            <Bar dataKey="Causation_Payment" name="Causation Payment (at Base LMP)" fill="#82ca9d" radius={[4, 4, 0, 0]}>
                <LabelList dataKey="Causation_Payment" position="top" formatter={(value) => formatNumber(value,0)} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

    </div>
  );
}

export default ComparisonCharts;
