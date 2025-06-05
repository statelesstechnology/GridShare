import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import SignupForm from './SignupForm'; // Adjust path as necessary

describe('SignupForm Component', () => {
  beforeEach(() => {
    global.fetch.mockClear();
    // Default successful fetch mock for signup
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ message: 'User created successfully', user_id: 123 }),
    });
  });

  test('renders input fields and submit button', () => {
    render(<SignupForm />);

    expect(screen.getByLabelText(/username/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /signup/i })).toBeInTheDocument();
  });

  test('allows user to type into input fields', async () => {
    render(<SignupForm />);
    const user = userEvent.setup();

    await user.type(screen.getByLabelText(/username/i), 'newsignup');
    expect(screen.getByLabelText(/username/i)).toHaveValue('newsignup');

    await user.type(screen.getByLabelText(/email/i), 'newsignup@example.com');
    expect(screen.getByLabelText(/email/i)).toHaveValue('newsignup@example.com');

    await user.type(screen.getByLabelText(/password/i), 'securepassword!@#');
    expect(screen.getByLabelText(/password/i)).toHaveValue('securepassword!@#');
  });

  test('handles successful signup', async () => {
    render(<SignupForm />);
    const user = userEvent.setup();

    const usernameInput = screen.getByLabelText(/username/i);
    const emailInput = screen.getByLabelText(/email/i);
    const passwordInput = screen.getByLabelText(/password/i);
    const signupButton = screen.getByRole('button', { name: /signup/i });

    await user.type(usernameInput, 'testsignup');
    await user.type(emailInput, 'testsignup@example.com');
    await user.type(passwordInput, 'password123');
    await user.click(signupButton);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith('/api/signup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: 'testsignup',
          email: 'testsignup@example.com',
          password: 'password123'
        }),
      });
    });

    // Check for success message displayed in the component
    const successMessage = await screen.findByText(/signup successful! user id: 123/i);
    expect(successMessage).toBeInTheDocument();

    // Check if form fields are cleared after successful signup (if implemented)
    expect(usernameInput).toHaveValue('');
    expect(emailInput).toHaveValue('');
    expect(passwordInput).toHaveValue('');
  });

  test('handles failed signup (e.g., user already exists)', async () => {
    global.fetch.mockResolvedValueOnce({ // Override default for this test
      ok: false,
      status: 409, // Conflict
      json: async () => ({ error: 'Username already exists' }),
    });

    render(<SignupForm />);
    const user = userEvent.setup();

    await user.type(screen.getByLabelText(/username/i), 'existinguser');
    await user.type(screen.getByLabelText(/email/i), 'existing@example.com');
    await user.type(screen.getByLabelText(/password/i), 'password123');
    await user.click(screen.getByRole('button', { name: /signup/i }));

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledTimes(1);
    });

    const errorMessage = await screen.findByText(/error: username already exists/i);
    expect(errorMessage).toBeInTheDocument();
  });

  test('handles missing fields client-side or server-side', async () => {
    // This test assumes client-side validation via `required` attribute on inputs
    // or specific logic in handleSubmit to prevent fetch if fields are empty.
    // If validation is purely server-side, the fetch would be called.

    render(<SignupForm />);
    const user = userEvent.setup();
    const signupButton = screen.getByRole('button', { name: /signup/i });

    // Attempt to submit with empty username (if client-side validation is simple)
    // For HTML5 'required', submit event might not even fire or fetch not called.
    // If component has its own JS validation that sets a message:
    await user.type(screen.getByLabelText(/email/i), 'test@example.com');
    await user.type(screen.getByLabelText(/password/i), 'password123');
    // Username is left empty

    // If using HTML5 validation, clicking the button on a form with required fields
    // that are empty won't trigger the submit handler in the same way.
    // We're testing if our component's submit handler or built-in validation catches it.
    // For this example, let's assume the component's handler is called and makes a fetch
    // and the backend returns a 400.

    global.fetch.mockResolvedValueOnce({
      ok: false,
      status: 400,
      json: async () => ({ error: 'Missing required fields' }),
    });

    await user.click(signupButton);

    // If there's client-side logic that prevents fetch:
    // await waitFor(() => expect(global.fetch).not.toHaveBeenCalled());
    // expect(await screen.findByText(/username is required/i)).toBeInTheDocument();

    // If fetch is called and server responds with error:
    await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledTimes(1)
    });
    expect(await screen.findByText(/error: missing required fields/i)).toBeInTheDocument();
  });

});
