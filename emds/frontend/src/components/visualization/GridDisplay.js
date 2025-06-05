import React, { useCallback, useEffect } from 'react'; // Removed useState as nodes/edges now fully controlled by props
import ReactFlow, {
  Background,
  Controls,
  useNodesState,
  useEdgesState,
  addEdge,
  MarkerType,
} from '@reactflow/core';
import '@reactflow/core/dist/style.css';

// Basic styles for nodes - can be expanded with custom node types
const baseNodeStyles = {
  bus: { backgroundColor: '#007bff', color: 'white', padding: '10px', borderRadius: '5px', border: '1px solid #0056b3', width: 'auto', minWidth: 120, textAlign: 'center', fontSize: '10px' },
  generator: { backgroundColor: '#28a745', color: 'white', padding: '8px', borderRadius: '5px', border: '1px solid #1e7e34', width: 'auto', minWidth:100, textAlign: 'center', fontSize: '10px' },
  load: { backgroundColor: '#dc3545', color: 'white', padding: '8px', borderRadius: '5px', border: '1px solid #c82333', width: 'auto', minWidth:100, textAlign: 'center', fontSize: '10px' },
};

const BUS_Y_POSITION = 200;
const GEN_LOAD_Y_OFFSET = 120;

function GridDisplay({ scenarioData, simulationResultData }) {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  const onConnect = useCallback((params) => setEdges((eds) => addEdge(params, eds)), [setEdges]);

  // Effect to build the initial grid structure from scenarioData
  useEffect(() => {
    if (!scenarioData) {
      setNodes([]); // Clear nodes if no scenario data
      setEdges([]); // Clear edges if no scenario data
      return;
    }

    const newNodes = [];
    const newEdges = [];
    const busMap = new Map();

    // Process Buses
    const scenarioBuses = scenarioData.grid_config?.buses || [];
    const numBuses = scenarioData.grid_config?.num_buses || 0;

    for (let i = 0; i < numBuses; i++) {
      const busDetails = scenarioBuses.find(b => b.id === (i + 1)) || {}; // Find by 1-based ID
      const busId = `bus-${i + 1}`;
      const busLabel = busDetails.name ? `Bus ${i + 1} (${busDetails.name})` : `Bus ${i + 1}`;
      const position = { x: (i + 1) * 220, y: BUS_Y_POSITION };
      newNodes.push({
        id: busId,
        type: 'default',
        data: { label: busLabel, originalLabel: busLabel }, // Store original for updates
        position: position,
        style: { ...baseNodeStyles.bus }, // Start with base style
      });
      busMap.set(i + 1, { id: busId, position, label: busLabel });
    }

    // Process Generators
    (scenarioData.generator_data || []).forEach((gen, index) => {
      const genId = `gen-${gen.id}`; // Use actual ID from data
      const busNum = parseInt(gen.bus_id, 10);
      const parentBus = busMap.get(busNum);
      let position = { x: 50 + index * 160, y: BUS_Y_POSITION - GEN_LOAD_Y_OFFSET };
      if (parentBus) {
        position = { x: parentBus.position.x + (index % 3 - 1) * 60, y: parentBus.position.y - GEN_LOAD_Y_OFFSET };
      }
      const genLabel = `Gen ${gen.id}\n(${gen.capacity_mw} MW)`;
      newNodes.push({
        id: genId,
        data: { label: genLabel, originalLabel: genLabel },
        position: position,
        style: { ...baseNodeStyles.generator },
      });
      if (parentBus) {
        newEdges.push({
          id: `edge-${genId}-${parentBus.id}`,
          source: genId, target: parentBus.id, type: 'smoothstep',
          markerEnd: { type: MarkerType.ArrowClosed },
        });
      }
    });

    // Process Loads
    (scenarioData.load_data || []).forEach((load, index) => {
      const loadId = `load-${load.id}`; // Use actual ID
      const busNum = parseInt(load.bus_id, 10);
      const parentBus = busMap.get(busNum);
      let position = { x: 50 + index * 160, y: BUS_Y_POSITION + GEN_LOAD_Y_OFFSET };
      if (parentBus) {
        position = { x: parentBus.position.x + (index % 3 - 1) * 60, y: parentBus.position.y + GEN_LOAD_Y_OFFSET };
      }
      const loadLabel = `Load ${load.id}\n(${load.demand_mw} MW)`;
      newNodes.push({
        id: loadId,
        data: { label: loadLabel, originalLabel: loadLabel },
        position: position,
        style: { ...baseNodeStyles.load },
      });
      if (parentBus) {
        newEdges.push({
          id: `edge-${loadId}-${parentBus.id}`,
          source: parentBus.id, target: loadId, type: 'smoothstep',
          markerEnd: { type: MarkerType.ArrowClosed },
        });
      }
    });

    // Process Transmission Lines
    (scenarioData.transmission_data || []).forEach((line) => {
      const fromBus = busMap.get(parseInt(line.from_bus_id, 10));
      const toBus = busMap.get(parseInt(line.to_bus_id, 10));
      if (fromBus && toBus) {
        const lineLabel = `${line.id}\n(Limit: ${line.flow_limit_mw} MW)`;
        newEdges.push({
          id: `line-${line.id}`,
          source: fromBus.id, target: toBus.id,
          label: lineLabel, originalLabel: lineLabel, // Store original label
          type: 'straight',
          style: { strokeWidth: 2, stroke: '#888' }, // Base style for lines
          markerEnd: { type: MarkerType.ArrowClosed, width: 15, height: 15, color: '#888' },
        });
      }
    });

    setNodes(newNodes);
    setEdges(newEdges);

  }, [scenarioData, setNodes, setEdges]);


  // Effect to update visuals based on simulationResultData
  useEffect(() => {
    if (!simulationResultData || simulationResultData.status !== 'success') {
        // Reset to base scenario view if no results or if results indicate failure
        setNodes(nds => nds.map(n => ({ ...n, data: { ...n.data, label: n.data.originalLabel }, style: {...(n.style || {}), ...baseNodeStyles[n.id.split('-')[0]] } })));
        setEdges(eds => eds.map(e => ({ ...e, label: e.data?.originalLabel || e.label, style: { strokeWidth: 2, stroke: '#888' }, animated: false })));
        return;
    }

    // Update Nodes with Nodal Prices
    setNodes(nds => nds.map(node => {
        if (node.id.startsWith('bus-')) {
            const busNum = parseInt(node.id.split('-')[1], 10);
            let lmp = 'N/A';
            // Nodal prices might be in summary_results.nodal_prices_mwh (object with Bus_X keys)
            // or directly in operational_results.nodal_prices_mwh (array)
            const nodalPricesDict = simulationResultData.financial_results?.system_summary?.nodal_prices_mwh ||
                                  simulationResultData.operational_results?.nodal_prices_mwh;

            if (Array.isArray(nodalPricesDict) && busNum-1 < nodalPricesDict.length) { // Array from operational_results
                lmp = nodalPricesDict[busNum-1]?.toFixed(2);
            } else if (typeof nodalPricesDict === 'object' && nodalPricesDict !== null) { // Object from system_summary
                 lmp = nodalPricesDict[`Bus_${busNum}`]?.toFixed(2) || nodalPricesDict[busNum.toString()]?.toFixed(2);
            }

            return { ...node, data: { ...node.data, label: `${node.data.originalLabel}\nLMP: $${lmp}/MWh` } };
        }
        // Update Generator Nodes with Security Charges (if causation model)
        if (simulationResultData.simulation_type === 'causation' && node.id.startsWith('gen-')) {
            const genId = node.id.substring(4); // Remove "gen-" prefix
            const genResult = simulationResultData.final_causation_financials?.generator_details?.find(g => g.id === genId);
            if (genResult && genResult.security_charge > 0) {
                return {
                    ...node,
                    data: { ...node.data, label: `${node.data.originalLabel}\nSecCharge: $${genResult.security_charge.toFixed(0)}`},
                    style: { ...node.style, border: '3px solid red', borderColor: 'red' }
                };
            } else {
                 return { ...node, style: { ...node.style, border: baseNodeStyles.generator.border, borderColor: baseNodeStyles.generator.border.split(' ')[2] } }; // Reset border
            }
        }
        return node;
    }));

    // Update Edges with Line Flows and Congestion
    setEdges(eds => eds.map(edge => {
        if (edge.id.startsWith('line-')) {
            const lineId = edge.id.substring(5); // Remove "line-" prefix
            const lineResult = simulationResultData.financial_results?.line_details?.find(l => l.id === lineId) ||
                               simulationResultData.operational_results?.line_details?.find(l => l.id === lineId) ; // Check both possible locations

            if (lineResult) {
                const flow = lineResult.flow_mw;
                const limit = lineResult.flow_limit_mw;
                const loadingPercentage = limit > 0 ? Math.abs(flow) / limit : 0;
                let strokeColor = 'green';
                if (loadingPercentage > 0.95) strokeColor = 'red';
                else if (loadingPercentage > 0.75) strokeColor = 'orange';

                return {
                    ...edge,
                    label: `${edge.data?.originalLabel || edge.label}\nFlow: ${flow.toFixed(1)} MW`,
                    style: { ...edge.style, stroke: strokeColor, strokeWidth: Math.max(2, loadingPercentage * 5) },
                    animated: loadingPercentage > 0.75 // Animate if heavily loaded
                };
            }
        }
        return edge; // Return unchanged edge if no result or not a line
    }));

  }, [simulationResultData, setNodes, setEdges, scenarioData]); // Rerun if base scenarioData also changes, ensuring nodes/edges are from current scenario


  if (!scenarioData) {
    return <div style={{height: '500px', textAlign:'center', paddingTop:'50px'}}>Please load scenario data to display the grid.</div>;
  }

  return (
    <div style={{ height: '100%', minHeight: '500px', border: '1px solid #ddd', borderRadius: '8px', marginTop: '0px' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        fitView
        attributionPosition="bottom-left"
      >
        <Background variant="dots" gap={16} size={1} />
        <Controls />
      </ReactFlow>
    </div>
  );
}

export default GridDisplay;
