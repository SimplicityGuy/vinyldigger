import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, Route, Routes } from 'react-router-dom';
import SearchAnalysisPage from '../../src/pages/SearchAnalysisPage';
import * as api from '../../src/lib/api';

// Mock the API module
vi.mock('../../src/lib/api', () => ({
  getSearchAnalysis: vi.fn(),
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
      <Routes>
        <Route path="/searches/:id/analysis" element={children} />
      </Routes>
    </QueryClientProvider>
  </BrowserRouter>
);

describe('SearchAnalysisPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    queryClient.clear();
    window.history.pushState({}, '', '/searches/123/analysis');
  });

  it('renders loading state initially', () => {
    mockedApi.getSearchAnalysis.mockReturnValue(new Promise(() => {}));

    render(<SearchAnalysisPage />, { wrapper: Wrapper });

    expect(screen.getByText('Loading analysis...')).toBeInTheDocument();
  });

  it('renders analysis data when loaded', async () => {
    const mockAnalysis = {
      search_id: '123',
      total_results: 10,
      unique_items: 8,
      average_price: 25.99,
      price_range: { min: 10.0, max: 50.0 },
      sellers_analysis: {
        total_sellers: 5,
        top_sellers: [
          {
            seller_name: 'Top Seller',
            item_count: 3,
            average_price: 30.0,
            location: 'USA',
            reputation_score: 4.5,
          },
        ],
      },
      platform_breakdown: {
        discogs: { count: 6, average_price: 24.99 },
        ebay: { count: 4, average_price: 27.99 },
      },
      condition_breakdown: {
        'Mint': { count: 2, average_price: 45.0 },
        'Near Mint': { count: 5, average_price: 30.0 },
        'Very Good': { count: 3, average_price: 15.0 },
      },
      recommendations: [
        {
          type: 'best_deal',
          item_id: 'item1',
          reason: 'Lowest price for this condition',
          potential_savings: 10.0,
        },
      ],
    };

    mockedApi.getSearchAnalysis.mockResolvedValue(mockAnalysis);

    render(<SearchAnalysisPage />, { wrapper: Wrapper });

    await waitFor(() => {
      expect(screen.getByText('Search Analysis')).toBeInTheDocument();
      expect(screen.getByText('Overview')).toBeInTheDocument();
      expect(screen.getByText('10')).toBeInTheDocument(); // total results
      expect(screen.getByText('$25.99')).toBeInTheDocument(); // average price
    });

    // Check sellers analysis
    expect(screen.getByText('Top Sellers')).toBeInTheDocument();
    expect(screen.getByText('Top Seller')).toBeInTheDocument();

    // Check platform breakdown
    expect(screen.getByText('Platform Breakdown')).toBeInTheDocument();
    expect(screen.getByText('Discogs')).toBeInTheDocument();
    expect(screen.getByText('eBay')).toBeInTheDocument();

    // Check condition breakdown
    expect(screen.getByText('Condition Distribution')).toBeInTheDocument();
    expect(screen.getByText('Near Mint')).toBeInTheDocument();
  });

  it('handles error state', async () => {
    mockedApi.getSearchAnalysis.mockRejectedValue(new Error('Failed to load analysis'));

    render(<SearchAnalysisPage />, { wrapper: Wrapper });

    await waitFor(() => {
      expect(screen.getByText('Error loading analysis')).toBeInTheDocument();
    });
  });

  it('handles empty analysis data', async () => {
    const mockEmptyAnalysis = {
      search_id: '123',
      total_results: 0,
      unique_items: 0,
      average_price: 0,
      price_range: { min: 0, max: 0 },
      sellers_analysis: {
        total_sellers: 0,
        top_sellers: [],
      },
      platform_breakdown: {},
      condition_breakdown: {},
      recommendations: [],
    };

    mockedApi.getSearchAnalysis.mockResolvedValue(mockEmptyAnalysis);

    render(<SearchAnalysisPage />, { wrapper: Wrapper });

    await waitFor(() => {
      expect(screen.getByText('No results to analyze')).toBeInTheDocument();
    });
  });

  it('displays recommendations when available', async () => {
    const mockAnalysis = {
      search_id: '123',
      total_results: 5,
      unique_items: 5,
      average_price: 20.0,
      price_range: { min: 10.0, max: 30.0 },
      sellers_analysis: {
        total_sellers: 3,
        top_sellers: [],
      },
      platform_breakdown: {},
      condition_breakdown: {},
      recommendations: [
        {
          type: 'multi_item_seller',
          seller_name: 'BulkVinyl',
          item_count: 3,
          reason: 'This seller has 3 items from your search',
          potential_savings: 15.0,
        },
        {
          type: 'best_price',
          item_id: 'item2',
          reason: 'Best price for Near Mint condition',
          potential_savings: 5.0,
        },
      ],
    };

    mockedApi.getSearchAnalysis.mockResolvedValue(mockAnalysis);

    render(<SearchAnalysisPage />, { wrapper: Wrapper });

    await waitFor(() => {
      expect(screen.getByText('Recommendations')).toBeInTheDocument();
      expect(screen.getByText(/This seller has 3 items/)).toBeInTheDocument();
      expect(screen.getByText(/Best price for Near Mint/)).toBeInTheDocument();
    });
  });

  it('formats currency values correctly', async () => {
    const mockAnalysis = {
      search_id: '123',
      total_results: 1,
      unique_items: 1,
      average_price: 1234.56,
      price_range: { min: 1234.56, max: 1234.56 },
      sellers_analysis: {
        total_sellers: 1,
        top_sellers: [],
      },
      platform_breakdown: {},
      condition_breakdown: {},
      recommendations: [],
    };

    mockedApi.getSearchAnalysis.mockResolvedValue(mockAnalysis);

    render(<SearchAnalysisPage />, { wrapper: Wrapper });

    await waitFor(() => {
      expect(screen.getByText('$1,234.56')).toBeInTheDocument();
    });
  });
});
