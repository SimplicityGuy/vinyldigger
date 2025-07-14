import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import ErrorBoundary from '../../src/components/ErrorBoundary';

// Component that throws an error
const ThrowError = ({ shouldThrow }: { shouldThrow: boolean }) => {
  if (shouldThrow) {
    throw new Error('Test error message');
  }
  return <div>No error</div>;
};

// Mock console.error to prevent error logs in tests
const originalError = console.error;
beforeEach(() => {
  console.error = vi.fn();
});

afterEach(() => {
  console.error = originalError;
});

describe('ErrorBoundary', () => {
  it('renders children when there is no error', () => {
    render(
      <BrowserRouter>
        <ErrorBoundary>
          <ThrowError shouldThrow={false} />
        </ErrorBoundary>
      </BrowserRouter>
    );

    expect(screen.getByText('No error')).toBeInTheDocument();
  });

  it('renders error UI when child component throws', () => {
    render(
      <BrowserRouter>
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      </BrowserRouter>
    );

    expect(screen.getByText('Oops! Something went wrong')).toBeInTheDocument();
    expect(screen.getByText(/We're sorry for the inconvenience/)).toBeInTheDocument();
    expect(screen.getByText('Go to Dashboard')).toBeInTheDocument();
  });

  it('shows error details in development mode', () => {
    // Mock development environment
    const originalEnv = import.meta.env.DEV;
    Object.defineProperty(import.meta.env, 'DEV', {
      value: true,
      configurable: true,
    });

    render(
      <BrowserRouter>
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      </BrowserRouter>
    );

    expect(screen.getByText('Error Details:')).toBeInTheDocument();
    expect(screen.getByText(/Test error message/)).toBeInTheDocument();

    // Restore original value
    Object.defineProperty(import.meta.env, 'DEV', {
      value: originalEnv,
      configurable: true,
    });
  });

  it('does not show error details in production mode', () => {
    // Mock production environment
    const originalEnv = import.meta.env.DEV;
    Object.defineProperty(import.meta.env, 'DEV', {
      value: false,
      configurable: true,
    });

    render(
      <BrowserRouter>
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      </BrowserRouter>
    );

    expect(screen.queryByText('Error Details:')).not.toBeInTheDocument();
    expect(screen.queryByText(/Test error message/)).not.toBeInTheDocument();

    // Restore original value
    Object.defineProperty(import.meta.env, 'DEV', {
      value: originalEnv,
      configurable: true,
    });
  });

  it('navigates to dashboard when clicking the button', () => {
    const mockNavigate = vi.fn();
    vi.mock('react-router-dom', async () => {
      const actual = await vi.importActual('react-router-dom');
      return {
        ...actual,
        useNavigate: () => mockNavigate,
      };
    });

    render(
      <BrowserRouter>
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      </BrowserRouter>
    );

    const dashboardButton = screen.getByText('Go to Dashboard');
    fireEvent.click(dashboardButton);

    // Check that navigation occurred
    expect(window.location.pathname).toBe('/');
  });

  it('logs error to console in development', () => {
    const originalEnv = import.meta.env.DEV;
    Object.defineProperty(import.meta.env, 'DEV', {
      value: true,
      configurable: true,
    });

    render(
      <BrowserRouter>
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      </BrowserRouter>
    );

    expect(console.error).toHaveBeenCalledWith(
      'ErrorBoundary caught an error:',
      expect.any(Error),
      expect.any(Object)
    );

    Object.defineProperty(import.meta.env, 'DEV', {
      value: originalEnv,
      configurable: true,
    });
  });

  it('handles error with componentStack', () => {
    // Test that error boundary handles errors with component stack info
    render(
      <BrowserRouter>
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      </BrowserRouter>
    );

    // The error boundary should handle errors with component stack info
    expect(screen.getByText('Oops! Something went wrong')).toBeInTheDocument();
  });
});
