import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import LoginForm from './LoginForm'; // Adjust path as necessary

// Mock onLoginSuccess prop
const mockOnLoginSuccess = jest.fn();

describe('LoginForm Component', () => {
  beforeEach(() => {
    // Clear mocks and localStorage before each test
    mockOnLoginSuccess.mockClear();
    global.fetch.mockClear();
    localStorage.clear();
    // Set a default successful fetch mock, can be overridden in specific tests
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ token: 'test_token', user_id: 1, username: 'testuser' }),
    });
  });

  test('renders input fields and submit button', () => {
    render(<LoginForm onLoginSuccess={mockOnLoginSuccess} />);

    expect(screen.getByLabelText(/username/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /login/i })).toBeInTheDocument();
  });

  test('allows user to type into input fields', async () => {
    render(<LoginForm onLoginSuccess={mockOnLoginSuccess} />);
    const user = userEvent.setup();

    const usernameInput = screen.getByLabelText(/username/i);
    await user.type(usernameInput, 'testuser');
    expect(usernameInput).toHaveValue('testuser');

    const passwordInput = screen.getByLabelText(/password/i);
    await user.type(passwordInput, 'password123');
    expect(passwordInput).toHaveValue('password123');
  });

  test('handles successful login', async () => {
    render(<LoginForm onLoginSuccess={mockOnLoginSuccess} />);
    const user = userEvent.setup();

    const usernameInput = screen.getByLabelText(/username/i);
    const passwordInput = screen.getByLabelText(/password/i);
    const loginButton = screen.getByRole('button', { name: /login/i });

    await user.type(usernameInput, 'testuser');
    await user.type(passwordInput, 'correctpassword');
    await user.click(loginButton);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith('/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: 'testuser', password: 'correctpassword' }),
      });
    });

    await waitFor(() => {
      expect(mockOnLoginSuccess).toHaveBeenCalledWith('test_token', 1, 'testuser');
    });

    // Check localStorage (might need to spy on localStorage.setItem directly if issues)
    expect(localStorage.getItem('emds_token')).toBe('test_token');
    expect(localStorage.getItem('emds_user_id')).toBe('1');

    // Check for success message (if any is implemented directly in LoginForm)
    // For example, if there's a <p>{message}</p>
    // expect(screen.getByText(/login successful/i)).toBeInTheDocument();
  });

  test('handles failed login with error message', async () => {
    // Override default fetch mock for this test
    global.fetch.mockResolvedValueOnce({
      ok: false,
      status: 401,
      json: async () => ({ error: 'Invalid credentials' }),
    });

    render(<LoginForm onLoginSuccess={mockOnLoginSuccess} />);
    const user = userEvent.setup();

    const usernameInput = screen.getByLabelText(/username/i);
    const passwordInput = screen.getByLabelText(/password/i);
    const loginButton = screen.getByRole('button', { name: /login/i });

    await user.type(usernameInput, 'testuser');
    await user.type(passwordInput, 'wrongpassword');
    await user.click(loginButton);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledTimes(1);
    });

    expect(mockOnLoginSuccess).not.toHaveBeenCalled();
    expect(localStorage.getItem('emds_token')).toBeNull();

    // Check for error message displayed in the component
    const errorMessage = await screen.findByText(/error: invalid credentials/i);
    expect(errorMessage).toBeInTheDocument();
  });

   test('handles missing fields', async () => {
    render(<LoginForm onLoginSuccess={mockOnLoginSuccess} />);
    const user = userEvent.setup();
    const loginButton = screen.getByRole('button', { name: /login/i });

    await user.click(loginButton); // Click without filling fields

    // Check for a message related to missing fields
    // This depends on how LoginForm displays this error.
    // Assuming it sets a message state that's rendered in a <p>
    const errorMessage = await screen.findByText(/missing required fields/i); // Or similar message from your component
    expect(errorMessage).toBeInTheDocument();
    expect(global.fetch).not.toHaveBeenCalled();
    expect(mockOnLoginSuccess).not.toHaveBeenCalled();
  });

});
