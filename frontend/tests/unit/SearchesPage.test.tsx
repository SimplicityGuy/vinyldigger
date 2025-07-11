import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import userEvent from '@testing-library/user-event'
// Mock the API first
vi.mock('@/lib/api', () => ({
  searchApi: {
    getSearches: vi.fn(),
    createSearch: vi.fn(),
    deleteSearch: vi.fn(),
    runSearch: vi.fn(),
    getSearchResults: vi.fn(),
  },
}))

// Import after mocks
import { SearchesPage } from '@/pages/SearchesPage'
import { searchApi } from '@/lib/api'

// Mock useAuth
vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({
    user: { id: '123', email: 'test@example.com' },
    isLoading: false,
  }),
}))

describe('SearchesPage', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    vi.clearAllMocks()
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false, gcTime: 0 },
        mutations: { retry: false },
      },
    })
  })

  const renderSearchesPage = () => {
    return render(
      <QueryClientProvider client={queryClient}>
        <SearchesPage />
      </QueryClientProvider>
    )
  }

  it('should render page header and create button', () => {
    ;(searchApi.getSearches as any).mockResolvedValue([])
    
    renderSearchesPage()

    expect(screen.getByText('Searches')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /New Search/i })).toBeInTheDocument()
  })

  it('should display searches list', async () => {
    const mockSearches = [
      {
        id: '1',
        name: 'Jazz Vinyl',
        query: 'jazz',
        platform: 'DISCOGS',
        check_interval_hours: 24,
        active: true,
        created_at: new Date().toISOString(),
      },
      {
        id: '2',
        name: 'Rock Albums',
        query: 'rock',
        platform: 'EBAY',
        check_interval_hours: 12,
        active: false,
        created_at: new Date().toISOString(),
      },
    ]
    ;(searchApi.getSearches as any).mockResolvedValue(mockSearches)

    renderSearchesPage()

    await waitFor(() => {
      expect(screen.getByText('Jazz Vinyl')).toBeInTheDocument()
      expect(screen.getByText('Rock Albums')).toBeInTheDocument()
      expect(screen.getByText('Discogs')).toBeInTheDocument()
      expect(screen.getByText('eBay')).toBeInTheDocument()
    })
  })

  it('should show empty state when no searches', async () => {
    ;(searchApi.getSearches as any).mockResolvedValue([])

    renderSearchesPage()

    await waitFor(() => {
      expect(screen.getByText(/No searches yet/i)).toBeInTheDocument()
    })
  })

  it('should handle creating a new search', async () => {
    const user = userEvent.setup()
    ;(searchApi.getSearches as any).mockResolvedValue([])
    ;(searchApi.createSearch as any).mockResolvedValue({
      id: '123',
      name: 'New Search',
      query: 'test query',
      platform: 'BOTH',
      check_interval_hours: 24,
    })

    renderSearchesPage()

    // Click create button
    const createButton = screen.getByRole('button', { name: /Create New Search/i })
    await user.click(createButton)

    // Fill form
    await waitFor(() => {
      expect(screen.getByText('Create New Search')).toBeInTheDocument()
    })

    const nameInput = screen.getByLabelText('Search Name')
    const queryInput = screen.getByLabelText('Search Query')
    
    await user.type(nameInput, 'New Search')
    await user.type(queryInput, 'test query')

    // Submit form
    const submitButton = screen.getByRole('button', { name: 'Create Search' })
    await user.click(submitButton)

    await waitFor(() => {
      expect(searchApi.createSearch).toHaveBeenCalledWith(expect.objectContaining({
        name: 'New Search',
        query: 'test query',
      }))
    })
  })

  it('should handle running a search', async () => {
    const user = userEvent.setup()
    const mockSearches = [{
      id: '1',
      name: 'Test Search',
      query: 'test',
      platform: 'DISCOGS',
      active: true,
      created_at: new Date().toISOString(),
    }]
    ;(searchApi.getSearches as any).mockResolvedValue(mockSearches)
    ;(searchApi.runSearch as any).mockResolvedValue({ message: 'Search started' })

    renderSearchesPage()

    await waitFor(() => {
      expect(screen.getByText('Test Search')).toBeInTheDocument()
    })

    // Click run button
    const runButton = screen.getByRole('button', { name: /Run/i })
    await user.click(runButton)

    await waitFor(() => {
      expect(searchApi.runSearch).toHaveBeenCalledWith('1')
    })
  })

  it('should handle deleting a search', async () => {
    const user = userEvent.setup()
    const mockSearches = [{
      id: '1',
      name: 'Test Search',
      query: 'test',
      platform: 'DISCOGS',
      active: true,
      created_at: new Date().toISOString(),
    }]
    ;(searchApi.getSearches as any).mockResolvedValue(mockSearches)
    ;(searchApi.deleteSearch as any).mockResolvedValue(undefined)

    renderSearchesPage()

    await waitFor(() => {
      expect(screen.getByText('Test Search')).toBeInTheDocument()
    })

    // Click delete button
    const deleteButton = screen.getByRole('button', { name: /Delete/i })
    await user.click(deleteButton)

    // Confirm deletion in dialog
    await waitFor(() => {
      expect(screen.getByText(/Are you sure/i)).toBeInTheDocument()
    })

    const confirmButton = screen.getByRole('button', { name: /Yes, delete/i })
    await user.click(confirmButton)

    await waitFor(() => {
      expect(searchApi.deleteSearch).toHaveBeenCalledWith('1')
    })
  })

  it('should display search results when available', async () => {
    const mockSearches = [{
      id: '1',
      name: 'Test Search',
      query: 'test',
      platform: 'DISCOGS',
      active: true,
      created_at: new Date().toISOString(),
    }]
    const mockResults = [
      {
        id: 'r1',
        item_id: 'item1',
        platform: 'DISCOGS',
        item_data: {
          title: 'Test Album',
          artist: 'Test Artist',
          price: 25.99,
        },
      },
    ]
    ;(searchApi.getSearches as any).mockResolvedValue(mockSearches)
    ;(searchApi.getSearchResults as any).mockResolvedValue(mockResults)

    renderSearchesPage()

    await waitFor(() => {
      expect(screen.getByText('Test Search')).toBeInTheDocument()
    })

    // View results
    const viewButton = screen.getByRole('button', { name: /View Results/i })
    await userEvent.click(viewButton)

    await waitFor(() => {
      expect(screen.getByText('Test Album')).toBeInTheDocument()
      expect(screen.getByText('Test Artist')).toBeInTheDocument()
      expect(screen.getByText('$25.99')).toBeInTheDocument()
    })
  })

  it('should show loading state', () => {
    ;(searchApi.getSearches as any).mockImplementation(() => new Promise(() => {}))

    renderSearchesPage()

    expect(screen.getByText(/Loading searches/i)).toBeInTheDocument()
  })

  it('should handle API errors gracefully', async () => {
    ;(searchApi.getSearches as any).mockRejectedValue(new Error('Failed to fetch'))

    renderSearchesPage()

    await waitFor(() => {
      expect(screen.getByText(/Failed to load searches/i)).toBeInTheDocument()
    })
  })
})