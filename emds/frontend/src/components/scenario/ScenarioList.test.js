import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ScenarioList from './ScenarioList'; // Adjust path

const mockOnEditScenario = jest.fn();
const mockOnDeleteScenario = jest.fn();
const mockOnViewResults = jest.fn(); // Added for new button

const mockScenarios = [
  { id: 1, name: 'Scenario Alpha', description: 'Alpha desc', user_id: 1, created_at: new Date().toISOString(), updated_at: new Date().toISOString() },
  { id: 2, name: 'Scenario Beta', description: 'Beta desc', user_id: 1, created_at: new Date().toISOString(), updated_at: new Date().toISOString() },
];

describe('ScenarioList Component', () => {
  beforeEach(() => {
    global.fetch.mockClear();
    mockOnEditScenario.mockClear();
    mockOnDeleteScenario.mockClear();
    mockOnViewResults.mockClear();
  });

  test('renders loading state initially', () => {
    global.fetch.mockImplementationOnce(() => new Promise(() => {})); // Keep it pending
    render(
      <ScenarioList
        userId={1}
        token="fake_token"
        onEditScenario={mockOnEditScenario}
        onDeleteScenario={mockOnDeleteScenario}
        onViewResults={mockOnViewResults}
        refreshKey={0}
      />
    );
    expect(screen.getByText(/loading scenarios.../i)).toBeInTheDocument();
  });

  test('renders list of scenarios on successful fetch', async () => {
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockScenarios,
    });
    render(
      <ScenarioList
        userId={1}
        token="fake_token"
        onEditScenario={mockOnEditScenario}
        onDeleteScenario={mockOnDeleteScenario}
        onViewResults={mockOnViewResults}
        refreshKey={0}
      />
    );

    expect(await screen.findByText('Scenario Alpha')).toBeInTheDocument();
    expect(screen.getByText('Scenario Beta')).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: /edit/i }).length).toBe(2);
    expect(screen.getAllByRole('button', { name: /delete/i }).length).toBe(2);
    expect(screen.getAllByRole('button', { name: /view results/i }).length).toBe(2);
  });

  test('renders error message on fetch failure', async () => {
    global.fetch.mockRejectedValueOnce(new Error('API is down'));
    render(
      <ScenarioList
        userId={1}
        token="fake_token"
        onEditScenario={mockOnEditScenario}
        onDeleteScenario={mockOnDeleteScenario}
        onViewResults={mockOnViewResults}
        refreshKey={0}
      />
    );
    expect(await screen.findByText(/error loading scenarios: api is down/i)).toBeInTheDocument();
  });

  test('renders "no scenarios found" message when list is empty', async () => {
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => [],
    });
    render(
      <ScenarioList
        userId={1}
        token="fake_token"
        onEditScenario={mockOnEditScenario}
        onDeleteScenario={mockOnDeleteScenario}
        onViewResults={mockOnViewResults}
        refreshKey={0}
      />
    );
    expect(await screen.findByText(/no scenarios found. create one!/i)).toBeInTheDocument();
  });

  test('calls onEditScenario with scenario data when Edit button is clicked', async () => {
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => [mockScenarios[0]], // Render only one scenario for simplicity
    });
    const user = userEvent.setup();
    render(
      <ScenarioList
        userId={1}
        token="fake_token"
        onEditScenario={mockOnEditScenario}
        onDeleteScenario={mockOnDeleteScenario}
        onViewResults={mockOnViewResults}
        refreshKey={0}
      />
    );

    const editButton = await screen.findByRole('button', { name: /edit/i });
    await user.click(editButton);
    expect(mockOnEditScenario).toHaveBeenCalledWith(mockScenarios[0]);
  });

  test('calls onDeleteScenario with scenario ID when Delete button is clicked', async () => {
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => [mockScenarios[1]],
    });
    const user = userEvent.setup();
    render(
      <ScenarioList
        userId={1}
        token="fake_token"
        onEditScenario={mockOnEditScenario}
        onDeleteScenario={mockOnDeleteScenario}
        onViewResults={mockOnViewResults}
        refreshKey={0}
      />
    );

    const deleteButton = await screen.findByRole('button', { name: /delete/i });
    await user.click(deleteButton);
    expect(mockOnDeleteScenario).toHaveBeenCalledWith(mockScenarios[1].id);
  });

  test('calls onViewResults with scenario ID when "View Results" button is clicked', async () => {
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => [mockScenarios[0]],
    });
    const user = userEvent.setup();
    render(
      <ScenarioList
        userId={1}
        token="fake_token"
        onEditScenario={mockOnEditScenario}
        onDeleteScenario={mockOnDeleteScenario}
        onViewResults={mockOnViewResults} // Pass the new prop
        refreshKey={0}
      />
    );

    const viewResultsButton = await screen.findByRole('button', { name: /view results/i });
    await user.click(viewResultsButton);
    expect(mockOnViewResults).toHaveBeenCalledWith(mockScenarios[0].id);
  });

  test('refetches scenarios when refreshKey changes', async () => {
    global.fetch.mockResolvedValueOnce({ ok: true, json: async () => [mockScenarios[0]] });
    const { rerender } = render(
      <ScenarioList userId={1} token="token" refreshKey={0}
        onEditScenario={mockOnEditScenario}
        onDeleteScenario={mockOnDeleteScenario}
        onViewResults={mockOnViewResults}
      />
    );
    await screen.findByText(mockScenarios[0].name); // Wait for initial render
    expect(global.fetch).toHaveBeenCalledTimes(1);

    global.fetch.mockResolvedValueOnce({ ok: true, json: async () => [mockScenarios[1]] });
    rerender(
      <ScenarioList userId={1} token="token" refreshKey={1} // Changed refreshKey
       onEditScenario={mockOnEditScenario}
       onDeleteScenario={mockOnDeleteScenario}
       onViewResults={mockOnViewResults}
      />
    );
    await screen.findByText(mockScenarios[1].name); // Wait for re-render with new data
    expect(global.fetch).toHaveBeenCalledTimes(2); // Fetch called again
  });

});
