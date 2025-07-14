import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import DashboardPage from '../../src/pages/DashboardPage';
import * as api from '../../src/lib/api';
import { AuthProvider } from '../../src/hooks/useAuth';

// Mock the API module
vi.mock('../../src/lib/api', () => ({
  getCollectionStatus: vi.fn(),
  getRecentSearches: vi.fn(),
  getSyncStatus: vi.fn(),
  getConfig: vi.fn(),
  syncCollection: vi.fn(),
}));

const mockedApi = api as vi.Mocked<typeof api>;

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: false },
    mutations: { retry: false },
  },
});

const Wrapper = ({ children }: { children: React.ReactNode }) => (
  <BrowserRouter>
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        {children}
      </AuthProvider>
    </QueryClientProvider>
  </BrowserRouter>
);

describe('DashboardPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    queryClient.clear();
  });

  it('renders loading state initially', () => {
    // Mock API calls to return pending promises
    mockedApi.getCollectionStatus.mockReturnValue(new Promise(() => {}));
    mockedApi.getRecentSearches.mockReturnValue(new Promise(() => {}));
    mockedApi.getSyncStatus.mockReturnValue(new Promise(() => {}));
    mockedApi.getConfig.mockReturnValue(new Promise(() => {}));

    render(<DashboardPage />, { wrapper: Wrapper });

    // Check for loading skeletons
    expect(screen.getAllByTestId('skeleton')).toHaveLength(4);
  });

  it('renders dashboard content when data is loaded', async () => {
    // Mock successful API responses
    mockedApi.getCollectionStatus.mockResolvedValue({
      collection_size: 100,
      want_list_size: 50,
    });

    mockedApi.getRecentSearches.mockResolvedValue([
      {
        id: '1',
        name: 'Test Search',
        query: 'test query',
        platforms: ['discogs'],
        check_interval_hours: 24,
        last_checked: new Date().toISOString(),
        is_active: true,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    ]);

    mockedApi.getSyncStatus.mockResolvedValue({
      collection_sync_status: 'idle',
      wantlist_sync_status: 'idle',
      last_collection_sync: new Date().toISOString(),
      last_wantlist_sync: new Date().toISOString(),
    });

    mockedApi.getConfig.mockResolvedValue({
      platforms: {
        discogs: { enabled: true, has_credentials: true },
        ebay: { enabled: true, has_credentials: true },
      },
    });

    render(<DashboardPage />, { wrapper: Wrapper });

    // Wait for content to load
    await waitFor(() => {
      expect(screen.getByText('Collection')).toBeInTheDocument();
      expect(screen.getByText('100 items')).toBeInTheDocument();
      expect(screen.getByText('Want List')).toBeInTheDocument();
      expect(screen.getByText('50 items')).toBeInTheDocument();
    });

    // Check for recent searches
    expect(screen.getByText('Recent Searches')).toBeInTheDocument();
    expect(screen.getByText('Test Search')).toBeInTheDocument();
  });

  it('handles empty recent searches', async () => {
    mockedApi.getCollectionStatus.mockResolvedValue({
      collection_size: 0,
      want_list_size: 0,
    });

    mockedApi.getRecentSearches.mockResolvedValue([]);

    mockedApi.getSyncStatus.mockResolvedValue({
      collection_sync_status: 'idle',
      wantlist_sync_status: 'idle',
      last_collection_sync: null,
      last_wantlist_sync: null,
    });

    mockedApi.getConfig.mockResolvedValue({
      platforms: {
        discogs: { enabled: true, has_credentials: false },
        ebay: { enabled: true, has_credentials: false },
      },
    });

    render(<DashboardPage />, { wrapper: Wrapper });

    await waitFor(() => {
      expect(screen.getByText('No saved searches yet')).toBeInTheDocument();
    });
  });

  it('handles sync button click', async () => {
    const mockSyncCollection = vi.fn().mockResolvedValue({});
    mockedApi.syncCollection = mockSyncCollection;

    mockedApi.getCollectionStatus.mockResolvedValue({
      collection_size: 100,
      want_list_size: 50,
    });

    mockedApi.getRecentSearches.mockResolvedValue([]);

    mockedApi.getSyncStatus.mockResolvedValue({
      collection_sync_status: 'idle',
      wantlist_sync_status: 'idle',
      last_collection_sync: null,
      last_wantlist_sync: null,
    });

    mockedApi.getConfig.mockResolvedValue({
      platforms: {
        discogs: { enabled: true, has_credentials: true },
        ebay: { enabled: false, has_credentials: false },
      },
    });

    render(<DashboardPage />, { wrapper: Wrapper });

    await waitFor(() => {
      expect(screen.getByText('Sync All')).toBeInTheDocument();
    });

    // Click sync button
    const syncButton = screen.getByText('Sync All');
    syncButton.click();

    await waitFor(() => {
      expect(mockSyncCollection).toHaveBeenCalled();
    });
  });

  it('displays sync progress when syncing', async () => {
    mockedApi.getCollectionStatus.mockResolvedValue({
      collection_size: 100,
      want_list_size: 50,
    });

    mockedApi.getRecentSearches.mockResolvedValue([]);

    mockedApi.getSyncStatus.mockResolvedValue({
      collection_sync_status: 'running',
      wantlist_sync_status: 'running',
      last_collection_sync: null,
      last_wantlist_sync: null,
    });

    mockedApi.getConfig.mockResolvedValue({
      platforms: {
        discogs: { enabled: true, has_credentials: true },
        ebay: { enabled: false, has_credentials: false },
      },
    });

    render(<DashboardPage />, { wrapper: Wrapper });

    await waitFor(() => {
      expect(screen.getByText('Syncing...')).toBeInTheDocument();
    });
  });

  it('handles API errors gracefully', async () => {
    mockedApi.getCollectionStatus.mockRejectedValue(new Error('API Error'));
    mockedApi.getRecentSearches.mockRejectedValue(new Error('API Error'));
    mockedApi.getSyncStatus.mockRejectedValue(new Error('API Error'));
    mockedApi.getConfig.mockRejectedValue(new Error('API Error'));

    render(<DashboardPage />, { wrapper: Wrapper });

    // The component should still render without crashing
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
  });
});
