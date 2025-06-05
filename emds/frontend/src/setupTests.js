// jest-dom adds custom jest matchers for asserting on DOM nodes.
// allows you to do things like:
// expect(element).toHaveTextContent(/react/i)
// learn more: https://github.com/testing-library/jest-dom
import '@testing-library/jest-dom';

// Mock localStorage for all tests
const localStorageMock = (function() {
  let store = {};
  return {
    getItem: function(key) {
      return store[key] || null;
    },
    setItem: function(key, value) {
      store[key] = value.toString();
    },
    removeItem: function(key) {
      delete store[key];
    },
    clear: function() {
      store = {};
    }
  };
})();

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock
});

// Mock global fetch
global.fetch = jest.fn(() =>
  Promise.resolve({
    ok: true,
    json: () => Promise.resolve({}),
  })
);

// Optional: Suppress console.error and console.log during tests
// beforeEach(() => {
//   jest.spyOn(console, 'error').mockImplementation(jest.fn());
//   jest.spyOn(console, 'log').mockImplementation(jest.fn());
// });

// afterEach(() => {
//   jest.restoreAllMocks();
// });
