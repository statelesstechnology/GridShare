import React from 'react';
import { render, screen, fireEvent, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ScenarioForm from './ScenarioForm'; // Adjust path

// Mock GridDisplay as it's complex and not the focus of this unit test
jest.mock('../visualization/GridDisplay', () => () => <div>Mocked GridDisplay</div>);

describe('ScenarioForm Component', () => {
  const mockOnSave = jest.fn();
  const mockOnCancel = jest.fn();

  const baseProps = {
    onSave: mockOnSave,
    onCancel: mockOnCancel,
    scenarioToEdit: null,
  };

  beforeEach(() => {
    mockOnSave.mockClear();
    mockOnCancel.mockClear();
  });

  test('renders basic fields (name, description, num_buses)', () => {
    render(<ScenarioForm {...baseProps} />);
    expect(screen.getByLabelText(/name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/description/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/number of buses/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /save scenario/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument();
  });

  test('allows typing in name, description, and num_buses', async () => {
    const user = userEvent.setup();
    render(<ScenarioForm {...baseProps} />);

    const nameInput = screen.getByLabelText(/name/i);
    await user.type(nameInput, 'My Test Scenario');
    expect(nameInput).toHaveValue('My Test Scenario');

    const descInput = screen.getByLabelText(/description/i);
    await user.type(descInput, 'A detailed description.');
    expect(descInput).toHaveValue('A detailed description.');

    const numBusesInput = screen.getByLabelText(/number of buses/i);
    // await user.clear(numBusesInput); // userEvent.type will append, clear first if needed
    fireEvent.change(numBusesInput, { target: { value: '5' } }); // Using fireEvent for number input
    expect(numBusesInput).toHaveValue(5);
  });

  test('adds and removes a generator', async () => {
    const user = userEvent.setup();
    render(<ScenarioForm {...baseProps} />);

    const addGeneratorButton = screen.getByRole('button', { name: /add generator/i });
    await user.click(addGeneratorButton);

    // Check if generator fields appear (e.g., find by placeholder or a common label)
    // This assumes generator items are identifiable, e.g., within a div.
    // Let's assume each generator group has a "Generator ID" input.
    let generatorIdInputs = screen.queryAllByPlaceholderText(/id \(e.g. g1\)/i);
    expect(generatorIdInputs.length).toBe(1);
    expect(screen.getByText(/generator 1 \(id: g1\)/i)).toBeInTheDocument();


    // Add another generator
    await user.click(addGeneratorButton);
    generatorIdInputs = screen.queryAllByPlaceholderText(/id \(e.g. g1\)/i);
    expect(generatorIdInputs.length).toBe(2);
    expect(screen.getByText(/generator 2 \(id: g2\)/i)).toBeInTheDocument();


    // Remove the first generator
    // Find the remove button within the first generator's group/section.
    // This requires the DOM structure to allow selecting specific remove buttons.
    // Assuming each generator group has a "Remove" button.
    const removeButtons = screen.getAllByRole('button', { name: /remove/i });
    await user.click(removeButtons[0]); // Click the first remove button

    generatorIdInputs = screen.queryAllByPlaceholderText(/id \(e.g. g1\)/i);
    expect(generatorIdInputs.length).toBe(1);
    // The remaining generator should now be "Generator 1" effectively, but its internal ID might still be G2
    // The text "Generator X (ID: Y)" needs to be checked carefully.
    // After removing the first one (G1), the one that was G2 should remain.
    // The component might re-label them or keep original IDs. The test should reflect component behavior.
    // Let's assume the component re-renders and the remaining one is now the first in the list.
    // The key part is that one set of inputs is gone.
    // If IDs are stable, check for G2's inputs.
    expect(screen.queryByText(/generator 1 \(id: g1\)/i)).toBeNull(); // Assuming G1 was removed
    expect(screen.getByDisplayValue('G2')).toBeInTheDocument(); // Check if G2's ID input is still there
  });


  test('populates form when scenarioToEdit prop is provided', () => {
    const scenarioToEdit = {
      name: 'Existing Scenario',
      description: 'Loaded from prop.',
      grid_config: { num_buses: 3 },
      generator_data: [{ id: 'G1', bus_id: 1, capacity_mw: 100, cost_energy_mwh: 20 }],
      load_data: [],
      transmission_data: [],
      contingency_data: { generator_outages: [], line_outages: [] },
    };
    render(<ScenarioForm {...baseProps} scenarioToEdit={scenarioToEdit} />);

    expect(screen.getByLabelText(/name/i)).toHaveValue('Existing Scenario');
    expect(screen.getByLabelText(/description/i)).toHaveValue('Loaded from prop.');
    expect(screen.getByLabelText(/number of buses/i)).toHaveValue(3);

    // Check if generator data is populated
    expect(screen.getByDisplayValue('G1')).toBeInTheDocument(); // Checks input with value 'G1'
    expect(screen.getByDisplayValue('100')).toBeInTheDocument(); // Capacity
  });


  test('calls onSave with correctly structured data on submit', async () => {
    const user = userEvent.setup();
    render(<ScenarioForm {...baseProps} />);

    // Fill basic info
    await user.type(screen.getByLabelText(/name/i), 'Full Scenario');
    fireEvent.change(screen.getByLabelText(/number of buses/i), { target: { value: '1' } });

    // Add and fill a generator
    await user.click(screen.getByRole('button', { name: /add generator/i }));
    await user.type(screen.getAllByPlaceholderText(/id \(e.g. g1\)/i)[0], 'Gen1');
    // For number inputs, fireEvent.change is often more reliable in RTL/JSDOM
    fireEvent.change(screen.getAllByPlaceholderText(/bus id/i)[0], { target: { value: '1' } });
    fireEvent.change(screen.getAllByPlaceholderText(/capacity \(mw\)/i)[0], { target: { value: '150' } });
    fireEvent.change(screen.getAllByPlaceholderText(/cost energy/i)[0], { target: { value: '25' } });


    // Submit form
    await user.click(screen.getByRole('button', { name: /save scenario/i }));

    expect(mockOnSave).toHaveBeenCalledTimes(1);
    const submittedData = mockOnSave.mock.calls[0][0];

    expect(submittedData.name).toBe('Full Scenario');
    expect(submittedData.grid_config.num_buses).toBe(1);
    expect(submittedData.generator_data.length).toBe(1);
    expect(submittedData.generator_data[0].id).toBe('Gen1');
    expect(submittedData.generator_data[0].bus_id).toBe(1); // Parsed as number
    expect(submittedData.generator_data[0].capacity_mw).toBe(150);
    expect(submittedData.generator_data[0].cost_energy_mwh).toBe(25);
  });

});
