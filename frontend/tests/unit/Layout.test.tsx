import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import Layout from '../../src/components/Layout';
import { AuthProvider } from '../../src/hooks/useAuth';
import * as tokenService from '../../src/lib/token-service';

// Mock the token service
vi.mock('../../src/lib/token-service', () => ({
  getAccessToken: vi.fn(),
  removeTokens: vi.fn(),
}));

const mockedTokenService = tokenService as vi.Mocked<typeof tokenService>;

const Wrapper = ({ children }: { children: React.ReactNode }) => (
  <BrowserRouter>
    <AuthProvider>
      {children}
    </AuthProvider>
  </BrowserRouter>
);

describe('Layout', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset token service
    mockedTokenService.getAccessToken.mockReturnValue(null);
    mockedTokenService.removeTokens.mockImplementation(() => {});
  });

  it('renders navigation links', () => {
    render(
      <Layout>
        <div>Test Content</div>
      </Layout>,
      { wrapper: Wrapper }
    );

    // Check for navigation links
    expect(screen.getByText('VinylDigger')).toBeInTheDocument();
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
    expect(screen.getByText('Searches')).toBeInTheDocument();
    expect(screen.getByText('Settings')).toBeInTheDocument();
  });

  it('renders children content', () => {
    render(
      <Layout>
        <div>Test Content</div>
      </Layout>,
      { wrapper: Wrapper }
    );

    expect(screen.getByText('Test Content')).toBeInTheDocument();
  });

  it('shows login link when not authenticated', () => {
    mockedTokenService.getAccessToken.mockReturnValue(null);

    render(
      <Layout>
        <div>Test Content</div>
      </Layout>,
      { wrapper: Wrapper }
    );

    expect(screen.getByText('Login')).toBeInTheDocument();
  });

  it('shows logout button when authenticated', () => {
    mockedTokenService.getAccessToken.mockReturnValue('test-token');

    render(
      <Layout>
        <div>Test Content</div>
      </Layout>,
      { wrapper: Wrapper }
    );

    expect(screen.getByText('Logout')).toBeInTheDocument();
  });

  it('handles logout click', () => {
    mockedTokenService.getAccessToken.mockReturnValue('test-token');

    render(
      <Layout>
        <div>Test Content</div>
      </Layout>,
      { wrapper: Wrapper }
    );

    const logoutButton = screen.getByText('Logout');
    fireEvent.click(logoutButton);

    expect(mockedTokenService.removeTokens).toHaveBeenCalled();
  });

  it('highlights active navigation link', () => {
    // Mock the current location
    Object.defineProperty(window, 'location', {
      value: { pathname: '/searches' },
      writable: true,
    });

    render(
      <Layout>
        <div>Test Content</div>
      </Layout>,
      { wrapper: Wrapper }
    );

    const searchesLink = screen.getByText('Searches');
    const linkElement = searchesLink.closest('a');
    expect(linkElement).toHaveClass('bg-gray-900');
  });

  it('renders responsive mobile menu button', () => {
    render(
      <Layout>
        <div>Test Content</div>
      </Layout>,
      { wrapper: Wrapper }
    );

    // Mobile menu button should be present
    const menuButton = screen.getByRole('button', { name: /open main menu/i });
    expect(menuButton).toBeInTheDocument();
  });

  it('toggles mobile menu on button click', () => {
    render(
      <Layout>
        <div>Test Content</div>
      </Layout>,
      { wrapper: Wrapper }
    );

    const menuButton = screen.getByRole('button', { name: /open main menu/i });

    // Initially mobile menu should be closed
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();

    // Click to open
    fireEvent.click(menuButton);

    // Mobile menu should be visible
    const mobileMenu = screen.getByRole('navigation', { name: /mobile/i });
    expect(mobileMenu).toBeInTheDocument();
  });
});
