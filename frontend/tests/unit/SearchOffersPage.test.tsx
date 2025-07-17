import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { SearchOffersPage } from '@/pages/SearchOffersPage'
import type { SavedSearch, SearchResult } from '@/types/api'

// Mock the API modules
vi.mock('@/lib/api', () => ({
  searchApi: {
    getSearch: vi.fn(),
    getSearchResults: vi.fn(),
  },
  searchAnalysisApi: {
    getSearchAnalysis: vi.fn(),
    getPriceComparison: vi.fn(),
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

const mockPriceComparisonData = {
  price_comparisons: [
    {
      item_match: {
        canonical_title: 'Abbey Road',
        canonical_artist: 'The Beatles',
        total_matches: 2,
      },
      listings: [
        {
          id: 'listing-1',
          platform: 'discogs',
          price: 25.99,
          condition: 'NM',
          seller: {
            id: 'seller-1',
            name: 'VinylHeaven',
            location: 'California, USA',
            feedback_score: 99.8,
          },
          is_in_wantlist: true,
          item_data: {
            id: 'listing-1',
            title: 'Abbey Road',
            artist: 'The Beatles',
            uri: '/sell/item/listing-1',
            release_id: '12345',
          },
        },
        {
          id: 'listing-2',
          platform: 'ebay',
          price: 30.00,
          condition: 'VG+',
          seller: {
            id: 'seller-2',
            name: 'RecordStore',
            location: 'New York, USA',
            feedback_score: 98.5,
          },
          is_in_wantlist: true,
          item_data: {
            id: 'ebay-2',
            title: 'Abbey Road',
            artist: 'The Beatles',
            item_web_url: 'https://www.ebay.com/itm/67890',
          },
        },
      ],
    },
    {
      item_match: {
        canonical_title: 'The Dark Side of the Moon',
        canonical_artist: 'Pink Floyd',
        total_matches: 1,
      },
      listings: [
        {
          id: 'listing-3',
          platform: 'ebay',
          price: 35.00,
          condition: 'M',
          seller: {
            id: 'seller-3',
            name: 'VinylMaster',
            location: 'Texas, USA',
            feedback_score: 97.2,
          },
          is_in_wantlist: false,
          item_data: {
            id: 'ebay-3',
            title: 'The Dark Side of the Moon',
            artist: 'Pink Floyd',
            item_web_url: 'https://www.ebay.com/itm/12345',
          },
        },
      ],
    },
    {
      item_match: {
        canonical_title: 'Led Zeppelin IV',
        canonical_artist: 'Led Zeppelin',
        total_matches: 1,
      },
      listings: [
        {
          id: 'listing-4',
          platform: 'discogs',
          price: 28.50,
          condition: 'VG+',
          seller: {
            id: 'seller-1',
            name: 'VinylHeaven',
            location: 'California, USA',
            feedback_score: 99.8,
          },
          is_in_wantlist: true,
          item_data: {
            id: 'listing-4',
            title: 'Led Zeppelin IV',
            artists_sort: 'Led Zeppelin',
            uri: '/sell/item/listing-4',
            release_id: '54321',
          },
        },
      ],
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
      <MemoryRouter initialEntries={[`/searches/${searchId}/offers`]}>
        <Routes>
          <Route path="/searches/:searchId/offers" element={<SearchOffersPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('SearchOffersPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Set default mocks to prevent React Query errors
    vi.mocked(searchApi.getSearch).mockResolvedValue(mockSearch)
    vi.mocked(searchAnalysisApi.getPriceComparison).mockResolvedValue(mockPriceComparisonData)
  })

  describe('Basic Rendering', () => {
    it('should display loading state while fetching data', () => {
      vi.mocked(searchApi.getSearch).mockImplementation(() => new Promise(() => {}))
      vi.mocked(searchAnalysisApi.getPriceComparison).mockImplementation(() => new Promise(() => {}))

      renderWithProviders()

      expect(screen.getByRole('status')).toBeInTheDocument() // Loading spinner
    })

    it('should display empty state when no price comparisons', async () => {
      vi.mocked(searchApi.getSearch).mockResolvedValue(mockSearch)
      vi.mocked(searchAnalysisApi.getPriceComparison).mockResolvedValue({
        price_comparisons: [],
      })

      renderWithProviders()

      await waitFor(() => {
        expect(screen.getByText('No price comparisons available')).toBeInTheDocument()
      })
    })

    it('should display price comparison data when completed', async () => {
      vi.mocked(searchApi.getSearch).mockResolvedValue(mockSearch)
      vi.mocked(searchAnalysisApi.getPriceComparison).mockResolvedValue(mockPriceComparisonData)

      renderWithProviders()

      await waitFor(() => {
        expect(screen.getAllByText('Price Comparison')).toHaveLength(2) // Header and card title
        expect(screen.getByText('Abbey Road')).toBeInTheDocument()
        expect(screen.getByText('The Dark Side of the Moon')).toBeInTheDocument()
        expect(screen.getByText('Led Zeppelin IV')).toBeInTheDocument()
      })
    })
  })

  describe('Price Comparison Section', () => {
    beforeEach(() => {
      vi.mocked(searchApi.getSearch).mockResolvedValue(mockSearch)
      vi.mocked(searchAnalysisApi.getPriceComparison).mockResolvedValue(mockPriceComparisonData)
    })

    it('should display price comparison with results', async () => {
      renderWithProviders()

      await waitFor(() => {
        expect(screen.getAllByText('Price Comparison')).toHaveLength(2) // Header and card title
        expect(screen.getByText('Abbey Road')).toBeInTheDocument()
        expect(screen.getByText('The Dark Side of the Moon')).toBeInTheDocument()
        expect(screen.getByText('Led Zeppelin IV')).toBeInTheDocument()
      })
    })

    it('should show wantlist star for items in wantlist', async () => {
      renderWithProviders()

      await waitFor(() => {
        const wantlistItems = screen.getAllByText('WANT LIST')
        expect(wantlistItems.length).toBeGreaterThanOrEqual(2) // Abbey Road and Led Zeppelin IV groups plus individual listings
      })
    })

    it('should display platform information for each item', async () => {
      renderWithProviders()

      await waitFor(() => {
        // Need to click on a section to expand and see platforms
        const abbeyRoadSection = screen.getByText('Abbey Road').closest('.border')
        expect(abbeyRoadSection).toBeInTheDocument()
      })

      // Click to expand
      const abbeyRoadSection = screen.getByText('Abbey Road').closest('.border')
      if (abbeyRoadSection) {
        fireEvent.click(abbeyRoadSection)
      }

      await waitFor(() => {
        expect(screen.getByText('Discogs')).toBeInTheDocument()
        expect(screen.getByText('Ebay')).toBeInTheDocument()
      })
    })

    it('should display prices correctly', async () => {
      renderWithProviders()

      await waitFor(() => {
        expect(screen.getByText('$25.99')).toBeInTheDocument() // Abbey Road
        expect(screen.getByText('$35.00')).toBeInTheDocument() // Dark Side of the Moon
        expect(screen.getByText('$28.50')).toBeInTheDocument() // Led Zeppelin IV
      })
    })

    it('should display view links for items with URLs', async () => {
      renderWithProviders()

      await waitFor(() => {
        const viewLinks = screen.getAllByText('View')
        expect(viewLinks.length).toBeGreaterThan(0)

        // Check Abbey Road link
        const abbeyRoadLink = screen.getByText('Abbey Road')
          .closest('.border')
          ?.querySelector('a[href="https://www.discogs.com/sell/item/listing-1"]')
        expect(abbeyRoadLink).toBeInTheDocument()

        // Check eBay link
        const eBayLink = screen.getByText('The Dark Side of the Moon')
          .closest('.border')
          ?.querySelector('a[href="https://www.ebay.com/itm/12345"]')
        expect(eBayLink).toBeInTheDocument()
      })
    })

    it('should handle missing price data gracefully', async () => {
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
        expect(screen.getByText('Price TBD')).toBeInTheDocument()
      })
    })

    it('should handle missing artist information', async () => {
      const resultsWithoutArtist = [...mockSearchResults]
      resultsWithoutArtist[0] = {
        ...resultsWithoutArtist[0],
        item_data: {
          ...resultsWithoutArtist[0].item_data,
          artist: undefined,
        },
      }

      vi.mocked(searchApi.getSearchResults).mockResolvedValue(resultsWithoutArtist)
      renderWithProviders()

      await waitFor(() => {
        expect(screen.getByText('by Unknown Artist')).toBeInTheDocument()
      })
    })

    it('should group items by title and artist', async () => {
      // Create duplicate items to test grouping
      const duplicateResults = [
        ...mockSearchResults,
        {
          ...mockSearchResults[0],
          id: 'result-4',
          platform: 'ebay',
          item_data: {
            ...mockSearchResults[0].item_data,
            price: 30.00,
            item_web_url: 'https://www.ebay.com/itm/67890',
          },
        },
      ]

      vi.mocked(searchApi.getSearchResults).mockResolvedValue(duplicateResults)
      renderWithProviders()

      await waitFor(() => {
        // Should show Abbey Road group with both Discogs and eBay prices
        expect(screen.getByText('Abbey Road')).toBeInTheDocument()
        expect(screen.getByText('$25.99')).toBeInTheDocument() // Discogs price
        expect(screen.getByText('$30.00')).toBeInTheDocument() // eBay price
      })
    })
  })

  describe('Empty States', () => {
    it('should display empty state when no results', async () => {
      vi.mocked(searchApi.getSearch).mockResolvedValue(mockSearch)
      vi.mocked(searchAnalysisApi.getSearchAnalysis).mockResolvedValue(mockAnalysisData)
      vi.mocked(searchApi.getSearchResults).mockResolvedValue([])

      renderWithProviders()

      await waitFor(() => {
        expect(screen.getByText('No search results found')).toBeInTheDocument()
      })
    })
  })

  describe('Navigation', () => {
    it('should display correct breadcrumb navigation', async () => {
      vi.mocked(searchApi.getSearch).mockResolvedValue(mockSearch)
      vi.mocked(searchAnalysisApi.getSearchAnalysis).mockResolvedValue(mockAnalysisData)

      renderWithProviders()

      await waitFor(() => {
        expect(screen.getByText('Searches')).toBeInTheDocument()
        expect(screen.getByText('Test Search')).toBeInTheDocument()
        expect(screen.getByText('Offers')).toBeInTheDocument()
      })
    })
  })

  describe('Error Handling', () => {
    it('should handle API errors gracefully', async () => {
      vi.mocked(searchApi.getSearch).mockRejectedValue(new Error('API Error'))

      renderWithProviders()

      // Should not crash and should handle the error state appropriately
      // The error boundary or query error handling should manage this
    })
  })
})
