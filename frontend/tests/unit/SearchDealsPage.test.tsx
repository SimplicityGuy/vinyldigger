import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { SearchDealsPage } from '@/pages/SearchDealsPage'
import type { SavedSearch, SearchResult } from '@/types/api'

// Mock the API modules
vi.mock('@/lib/api', () => ({
  searchApi: {
    getSearch: vi.fn(),
    getSearchResults: vi.fn(),
  },
  searchAnalysisApi: {
    getSearchAnalysis: vi.fn(),
    getMultiItemDeals: vi.fn(),
  },
}))

// Import mocked modules
import { searchApi, searchAnalysisApi } from '@/lib/api'

// Test data
const mockSearch: SavedSearch = {
  id: 'search-123',
  name: 'Test Search',
  query: 'vinyl records',
  platform: 'both',
  filters: {},
  is_active: true,
  check_interval_hours: 24,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
}

const mockSearchResults: SearchResult[] = [
  {
    id: 'result-1',
    search_id: 'search-123',
    platform: 'discogs',
    item_id: 'item-1',
    item_data: {
      id: 'listing-1',
      title: 'Abbey Road',
      artist: 'The Beatles',
      price: 25.99,
      uri: '/sell/item/listing-1',
      item_url: 'https://www.discogs.com/sell/item/listing-1',
    },
    is_in_collection: false,
    is_in_wantlist: true,
    created_at: '2024-01-01T00:00:00Z',
  },
  {
    id: 'result-2',
    search_id: 'search-123',
    platform: 'ebay',
    item_id: 'item-2',
    item_data: {
      id: 'ebay-2',
      title: 'The Dark Side of the Moon',
      artist: 'Pink Floyd',
      price: 35.00,
      item_web_url: 'https://www.ebay.com/itm/12345',
    },
    is_in_collection: false,
    is_in_wantlist: false,
    created_at: '2024-01-01T00:00:00Z',
  },
  {
    id: 'result-3',
    search_id: 'search-123',
    platform: 'discogs',
    item_id: 'item-3',
    item_data: {
      id: 'listing-3',
      title: 'Led Zeppelin IV',
      artists_sort: 'Led Zeppelin',
      current_price: 28.50,
    },
    is_in_collection: false,
    is_in_wantlist: true,
    created_at: '2024-01-01T00:00:00Z',
  },
]

const mockAnalysisData = {
  analysis_completed: true,
  analysis: {
    total_results: 50,
    total_sellers: 15,
    wantlist_matches: 10,
    multi_item_sellers: 5,
    min_price: 10.00,
    max_price: 100.00,
    avg_price: 35.50,
  },
  recommendations: [
    {
      id: 'rec-1',
      type: 'MULTI_ITEM',
      deal_score: 'EXCELLENT',
      score_value: 95,
      title: 'Bundle Deal from VinylHeaven',
      description: '3 items from your wantlist available',
      recommendation_reason: 'Save $15 on combined shipping',
      total_items: 3,
      wantlist_items: 2,
      total_value: 89.49,
      estimated_shipping: 12.00,
      total_cost: 101.49,
      potential_savings: 15.00,
      seller: {
        id: 'seller-1',
        name: 'VinylHeaven',
        location: 'California, USA',
        feedback_score: 99.8,
      },
      item_ids: ['result-1', 'result-3'],
    },
    {
      id: 'rec-2',
      type: 'MULTI_ITEM',
      deal_score: 'VERY_GOOD',
      score_value: 85,
      title: 'Good Bundle from RecordStore',
      description: '2 items including rare finds',
      recommendation_reason: 'Competitive pricing with fast shipping',
      total_items: 2,
      wantlist_items: 1,
      total_value: 60.99,
      estimated_shipping: null,
      total_cost: 60.99,
      potential_savings: null,
      seller: {
        id: null,
        name: 'RecordStore',
        location: null,
        feedback_score: null,
      },
      item_ids: ['result-2'],
    },
    {
      id: 'rec-3',
      type: 'PRICE_ALERT',
      deal_score: 'GOOD',
      score_value: 75,
      title: 'Price Drop Alert',
      description: 'Significant price reduction detected',
      recommendation_reason: '20% below average market price',
      total_items: 1,
      wantlist_items: 0,
      total_value: 25.00,
      estimated_shipping: 5.00,
      total_cost: 30.00,
      potential_savings: 10.00,
      seller: null,
      item_ids: [],
    },
  ],
  seller_analyses: [
    {
      rank: 1,
      total_items: 5,
      wantlist_items: 3,
      total_value: 150.00,
      overall_score: 95,
      estimated_shipping: 15.00,
      seller: {
        id: 'seller-1',
        name: 'VinylHeaven',
        location: 'California, USA',
        feedback_score: 99.8,
      },
    },
    {
      rank: 2,
      total_items: 3,
      wantlist_items: 1,
      total_value: 85.00,
      overall_score: 82,
      estimated_shipping: null,
      seller: {
        id: 'seller-2',
        name: 'RecordStore',
        location: 'New York, USA',
        feedback_score: 98.5,
      },
    },
  ],
}

const mockMultiItemDeals = {
  multi_item_deals: [
    {
      seller: {
        id: 'seller-1',
        name: 'VinylHeaven',
        location: 'California, USA',
        feedback_score: 99.8,
      },
      total_items: 3,
      wantlist_items: 2,
      total_value: 89.49,
      estimated_shipping: 12.00,
      total_cost: 101.49,
      potential_savings: 15.00,
      deal_score: 'EXCELLENT',
      item_ids: ['result-1', 'result-3'],
    },
    {
      seller: {
        id: null,
        name: 'RecordStore',
        location: null,
        feedback_score: null,
      },
      total_items: 2,
      wantlist_items: 1,
      total_value: 60.99,
      estimated_shipping: null,
      total_cost: 60.99,
      potential_savings: null,
      deal_score: 'VERY_GOOD',
      item_ids: ['result-2'],
    },
  ],
}

// Helper function to render component with providers
const renderWithProviders = (searchId = 'search-123') => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  })

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[`/searches/${searchId}/deals`]}>
        <Routes>
          <Route path="/searches/:searchId/deals" element={<SearchDealsPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('SearchDealsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Set default mocks to prevent React Query errors
    vi.mocked(searchApi.getSearch).mockResolvedValue(mockSearch)
    vi.mocked(searchAnalysisApi.getSearchAnalysis).mockResolvedValue(mockAnalysisData)
    vi.mocked(searchAnalysisApi.getMultiItemDeals).mockResolvedValue(mockMultiItemDeals)
    vi.mocked(searchApi.getSearchResults).mockResolvedValue(mockSearchResults)
  })

  describe('Basic Rendering', () => {
    it('should display loading state while fetching data', () => {
      vi.mocked(searchApi.getSearch).mockImplementation(() => new Promise(() => {}))
      vi.mocked(searchAnalysisApi.getSearchAnalysis).mockImplementation(() => new Promise(() => {}))
      vi.mocked(searchAnalysisApi.getMultiItemDeals).mockImplementation(() => new Promise(() => {}))
      vi.mocked(searchApi.getSearchResults).mockImplementation(() => new Promise(() => {}))

      renderWithProviders()

      expect(screen.getByRole('status')).toBeInTheDocument() // Loading spinner
    })

    it('should display message when analysis is not completed', async () => {
      vi.mocked(searchApi.getSearch).mockResolvedValue(mockSearch)
      vi.mocked(searchAnalysisApi.getSearchAnalysis).mockResolvedValue({
        analysis_completed: false,
        message: 'Analysis in progress',
      })
      vi.mocked(searchAnalysisApi.getMultiItemDeals).mockResolvedValue({ multi_item_deals: [] })
      vi.mocked(searchApi.getSearchResults).mockResolvedValue([])

      renderWithProviders()

      await waitFor(() => {
        expect(screen.getByText('Analysis in progress')).toBeInTheDocument()
      })
    })

    it('should display deals data when completed', async () => {
      vi.mocked(searchApi.getSearch).mockResolvedValue(mockSearch)
      vi.mocked(searchAnalysisApi.getSearchAnalysis).mockResolvedValue(mockAnalysisData)
      vi.mocked(searchAnalysisApi.getMultiItemDeals).mockResolvedValue(mockMultiItemDeals)
      vi.mocked(searchApi.getSearchResults).mockResolvedValue(mockSearchResults)

      renderWithProviders()

      await waitFor(() => {
        expect(screen.getByText('Search Deals')).toBeInTheDocument()
        expect(screen.getByText('50')).toBeInTheDocument() // total results
        expect(screen.getByText('10')).toBeInTheDocument() // wantlist matches
        expect(screen.getByText('5')).toBeInTheDocument() // multi-item sellers
      })
    })
  })

  describe('Multi-Item Deals Section', () => {
    beforeEach(() => {
      vi.mocked(searchApi.getSearch).mockResolvedValue(mockSearch)
      vi.mocked(searchApi.getSearchResults).mockResolvedValue(mockSearchResults)
      vi.mocked(searchAnalysisApi.getSearchAnalysis).mockResolvedValue(mockAnalysisData)
      vi.mocked(searchAnalysisApi.getMultiItemDeals).mockResolvedValue(mockMultiItemDeals)
    })

    it('should display multi-item deals section', async () => {
      renderWithProviders()

      await waitFor(() => {
        expect(screen.getAllByText('Multi-Item Deals')).toHaveLength(2) // Stats card and section heading
        expect(screen.getByText('EXCELLENT DEAL')).toBeInTheDocument()
        expect(screen.getByText('VERY GOOD DEAL')).toBeInTheDocument()
      })
    })

    it('should expand/collapse seller sections when clicked', async () => {
      renderWithProviders()

      await waitFor(() => {
        expect(screen.getByText('VinylHeaven')).toBeInTheDocument()
      })

      // Initially, item details should not be visible
      expect(screen.queryByText('Items in this deal:')).not.toBeInTheDocument()

      // Click on the first deal to expand it
      const firstDeal = screen.getByText('VinylHeaven').closest('.border')
      fireEvent.click(firstDeal!)

      // Now item details should be visible
      await waitFor(() => {
        expect(screen.getByText('Items in this deal:')).toBeInTheDocument()
        expect(screen.getByText('Abbey Road')).toBeInTheDocument()
        expect(screen.getByText('Led Zeppelin IV')).toBeInTheDocument()
      })

      // Click again to collapse
      fireEvent.click(firstDeal!)
      await waitFor(() => {
        expect(screen.queryByText('Items in this deal:')).not.toBeInTheDocument()
      })
    })

    it('should display item details with correct information', async () => {
      renderWithProviders()

      await waitFor(() => {
        expect(screen.getByText('VinylHeaven')).toBeInTheDocument()
      })

      // Expand the first deal
      const firstDeal = screen.getByText('VinylHeaven').closest('.border')
      fireEvent.click(firstDeal!)

      await waitFor(() => {
        // Check Abbey Road item
        const abbeyRoadItem = screen.getByText('Abbey Road').closest('.border')
        expect(abbeyRoadItem).toHaveTextContent('by The Beatles')
        expect(abbeyRoadItem).toHaveTextContent('$25.99')
        expect(abbeyRoadItem).toHaveTextContent('Discogs')

        // Check Led Zeppelin item
        const ledZepItem = screen.getByText('Led Zeppelin IV').closest('.border')
        expect(ledZepItem).toHaveTextContent('by Led Zeppelin')
        expect(ledZepItem).toHaveTextContent('$28.50')
      })
    })

    it('should show wantlist star for items in wantlist', async () => {
      renderWithProviders()

      await waitFor(() => {
        expect(screen.getByText('VinylHeaven')).toBeInTheDocument()
      })

      // Expand the first deal
      const firstDeal = screen.getByText('VinylHeaven').closest('.border')
      fireEvent.click(firstDeal!)

      await waitFor(() => {
        // Both items in this deal are in the wantlist
        const stars = screen.getAllByLabelText('In your wantlist')
        expect(stars).toHaveLength(2)
      })
    })

    it('should display view links for items with URLs', async () => {
      renderWithProviders()

      await waitFor(() => {
        expect(screen.getByText('VinylHeaven')).toBeInTheDocument()
      })

      // Expand the first deal
      const firstDeal = screen.getByText('VinylHeaven').closest('.border')
      fireEvent.click(firstDeal!)

      await waitFor(() => {
        const viewLinks = screen.getAllByText('View')
        expect(viewLinks).toHaveLength(1) // Only Abbey Road has a complete URL

        const abbeyRoadLink = screen.getByText('Abbey Road')
          .closest('.border')
          ?.querySelector('a[href="https://www.discogs.com/sell/item/listing-1"]')
        expect(abbeyRoadLink).toBeInTheDocument()
      })
    })

    it('should display price TBD for items without price', async () => {
      const resultsWithoutPrice = [...mockSearchResults]
      resultsWithoutPrice[0] = {
        ...resultsWithoutPrice[0],
        item_data: {
          ...resultsWithoutPrice[0].item_data,
          price: null,
        },
      }

      vi.mocked(searchApi.getSearchResults).mockResolvedValue(resultsWithoutPrice)
      renderWithProviders()

      await waitFor(() => {
        expect(screen.getByText('VinylHeaven')).toBeInTheDocument()
      })

      const firstDeal = screen.getByText('VinylHeaven').closest('.border')
      fireEvent.click(firstDeal!)

      await waitFor(() => {
        expect(screen.getByText('Price TBD')).toBeInTheDocument()
      })
    })
  })

  describe('Other Recommendations Section', () => {
    beforeEach(() => {
      vi.mocked(searchApi.getSearch).mockResolvedValue(mockSearch)
      vi.mocked(searchAnalysisApi.getSearchAnalysis).mockResolvedValue(mockAnalysisData)
      vi.mocked(searchAnalysisApi.getMultiItemDeals).mockResolvedValue(mockMultiItemDeals)
    })

    it('should display other recommendations section', async () => {
      renderWithProviders()

      await waitFor(() => {
        expect(screen.getByText('Other Recommendations')).toBeInTheDocument()
        expect(screen.getByText('Price Drop Alert')).toBeInTheDocument()
      })
    })
  })

  describe('Top Sellers Section', () => {
    it('should display top sellers information', async () => {
      vi.mocked(searchApi.getSearch).mockResolvedValue(mockSearch)
      vi.mocked(searchAnalysisApi.getSearchAnalysis).mockResolvedValue(mockAnalysisData)
      vi.mocked(searchAnalysisApi.getMultiItemDeals).mockResolvedValue(mockMultiItemDeals)

      renderWithProviders()

      await waitFor(() => {
        expect(screen.getByText('Top Sellers')).toBeInTheDocument()
        expect(screen.getByText('VinylHeaven')).toBeInTheDocument()
        expect(screen.getByText('RecordStore')).toBeInTheDocument()
        expect(screen.getByText('95% score')).toBeInTheDocument()
        expect(screen.getByText('82% score')).toBeInTheDocument()
      })
    })
  })

  describe('Edge Cases', () => {
    it('should handle missing seller information gracefully', async () => {
      vi.mocked(searchApi.getSearch).mockResolvedValue(mockSearch)
      vi.mocked(searchAnalysisApi.getSearchAnalysis).mockResolvedValue(mockAnalysisData)
      vi.mocked(searchAnalysisApi.getMultiItemDeals).mockResolvedValue(mockMultiItemDeals)

      renderWithProviders()

      await waitFor(() => {
        expect(screen.getByText('RecordStore')).toBeInTheDocument()
      })

      // This deal has null seller fields
      const dealElement = screen.getByText('RecordStore').closest('.border')
      expect(dealElement).not.toHaveTextContent('feedback')
      expect(dealElement).toHaveTextContent('RecordStore')
    })

    it('should display loading message when expanding deal with no loaded items', async () => {
      vi.mocked(searchApi.getSearch).mockResolvedValue(mockSearch)
      vi.mocked(searchAnalysisApi.getSearchAnalysis).mockResolvedValue(mockAnalysisData)
      vi.mocked(searchAnalysisApi.getMultiItemDeals).mockResolvedValue(mockMultiItemDeals)
      vi.mocked(searchApi.getSearchResults).mockResolvedValue([])

      renderWithProviders()

      await waitFor(() => {
        expect(screen.getByText('VinylHeaven')).toBeInTheDocument()
      })

      const firstDeal = screen.getByText('VinylHeaven').closest('.border')
      fireEvent.click(firstDeal!)

      await waitFor(() => {
        expect(screen.getByText('Loading item details...')).toBeInTheDocument()
      })
    })

    it('should handle items with missing artist information', async () => {
      const itemsWithoutArtist = [{
        ...mockSearchResults[0],
        item_data: {
          title: 'Unknown Album',
          price: 20.00,
        },
      }]

      vi.mocked(searchApi.getSearch).mockResolvedValue(mockSearch)
      vi.mocked(searchAnalysisApi.getSearchAnalysis).mockResolvedValue(mockAnalysisData)
      vi.mocked(searchAnalysisApi.getMultiItemDeals).mockResolvedValue(mockMultiItemDeals)
      vi.mocked(searchApi.getSearchResults).mockResolvedValue(itemsWithoutArtist)

      renderWithProviders()

      await waitFor(() => {
        expect(screen.getByText('VinylHeaven')).toBeInTheDocument()
      })

      const firstDeal = screen.getByText('VinylHeaven').closest('.border')
      fireEvent.click(firstDeal!)

      await waitFor(() => {
        expect(screen.getByText('by Unknown Artist')).toBeInTheDocument()
      })
    })
  })
})
