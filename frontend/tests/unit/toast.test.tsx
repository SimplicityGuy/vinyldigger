import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import {
  Toast,
  ToastAction,
  ToastClose,
  ToastDescription,
  ToastProvider,
  ToastTitle,
  ToastViewport,
} from '../../src/components/ui/toast';

describe('Toast Components', () => {
  describe('Toast', () => {
    it('renders toast with default variant', () => {
      render(
        <ToastProvider>
          <Toast>
            <ToastTitle>Test Toast</ToastTitle>
          </Toast>
          <ToastViewport />
        </ToastProvider>
      );

      const toast = screen.getByRole('alert');
      expect(toast).toBeInTheDocument();
      expect(toast).toHaveClass('bg-white');
    });

    it('renders toast with destructive variant', () => {
      render(
        <ToastProvider>
          <Toast variant="destructive">
            <ToastTitle>Error Toast</ToastTitle>
          </Toast>
          <ToastViewport />
        </ToastProvider>
      );

      const toast = screen.getByRole('alert');
      expect(toast).toHaveClass('bg-red-600');
    });
  });

  describe('ToastTitle', () => {
    it('renders toast title', () => {
      render(
        <ToastProvider>
          <Toast>
            <ToastTitle>Test Title</ToastTitle>
          </Toast>
          <ToastViewport />
        </ToastProvider>
      );

      expect(screen.getByText('Test Title')).toBeInTheDocument();
    });
  });

  describe('ToastDescription', () => {
    it('renders toast description', () => {
      render(
        <ToastProvider>
          <Toast>
            <ToastDescription>Test Description</ToastDescription>
          </Toast>
          <ToastViewport />
        </ToastProvider>
      );

      expect(screen.getByText('Test Description')).toBeInTheDocument();
    });
  });

  describe('ToastAction', () => {
    it('renders toast action button', () => {
      const handleClick = vi.fn();

      render(
        <ToastProvider>
          <Toast>
            <ToastTitle>Test Toast</ToastTitle>
            <ToastAction altText="Retry" onClick={handleClick}>
              Retry
            </ToastAction>
          </Toast>
          <ToastViewport />
        </ToastProvider>
      );

      const actionButton = screen.getByRole('button', { name: 'Retry' });
      expect(actionButton).toBeInTheDocument();

      fireEvent.click(actionButton);
      expect(handleClick).toHaveBeenCalledTimes(1);
    });

    it('applies correct styling to action button', () => {
      render(
        <ToastProvider>
          <Toast>
            <ToastAction altText="Undo">Undo</ToastAction>
          </Toast>
          <ToastViewport />
        </ToastProvider>
      );

      const actionButton = screen.getByRole('button', { name: 'Undo' });
      expect(actionButton).toHaveClass('ring-offset-white');
    });
  });

  describe('ToastClose', () => {
    it('renders close button', () => {
      render(
        <ToastProvider>
          <Toast>
            <ToastTitle>Test Toast</ToastTitle>
            <ToastClose />
          </Toast>
          <ToastViewport />
        </ToastProvider>
      );

      const closeButton = screen.getByRole('button', { name: /close/i });
      expect(closeButton).toBeInTheDocument();
      expect(closeButton).toHaveClass('opacity-0', 'group-hover:opacity-100');
    });

    it('shows X icon in close button', () => {
      render(
        <ToastProvider>
          <Toast>
            <ToastClose />
          </Toast>
          <ToastViewport />
        </ToastProvider>
      );

      const closeButton = screen.getByRole('button', { name: /close/i });
      const icon = closeButton.querySelector('svg');
      expect(icon).toBeInTheDocument();
    });
  });

  describe('ToastViewport', () => {
    it('renders viewport with correct positioning', () => {
      render(
        <ToastProvider>
          <ToastViewport />
        </ToastProvider>
      );

      const viewport = screen.getByRole('region', { name: 'Notifications (F8)' });
      expect(viewport).toBeInTheDocument();
      expect(viewport).toHaveClass('fixed', 'top-0', 'right-0');
    });

    it('renders multiple toasts', () => {
      render(
        <ToastProvider>
          <Toast>
            <ToastTitle>Toast 1</ToastTitle>
          </Toast>
          <Toast>
            <ToastTitle>Toast 2</ToastTitle>
          </Toast>
          <ToastViewport />
        </ToastProvider>
      );

      expect(screen.getByText('Toast 1')).toBeInTheDocument();
      expect(screen.getByText('Toast 2')).toBeInTheDocument();
    });
  });

  describe('Toast Integration', () => {
    it('renders complete toast with all components', () => {
      const handleAction = vi.fn();

      render(
        <ToastProvider>
          <Toast>
            <div className="grid gap-1">
              <ToastTitle>Success!</ToastTitle>
              <ToastDescription>Your changes have been saved.</ToastDescription>
            </div>
            <ToastAction altText="Undo changes" onClick={handleAction}>
              Undo
            </ToastAction>
            <ToastClose />
          </Toast>
          <ToastViewport />
        </ToastProvider>
      );

      expect(screen.getByText('Success!')).toBeInTheDocument();
      expect(screen.getByText('Your changes have been saved.')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Undo' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /close/i })).toBeInTheDocument();
    });

    it('renders destructive toast with error styling', () => {
      render(
        <ToastProvider>
          <Toast variant="destructive">
            <div className="grid gap-1">
              <ToastTitle>Error</ToastTitle>
              <ToastDescription>Something went wrong.</ToastDescription>
            </div>
          </Toast>
          <ToastViewport />
        </ToastProvider>
      );

      const toast = screen.getByRole('alert');
      expect(toast).toHaveClass('bg-red-600');
      expect(screen.getByText('Error')).toBeInTheDocument();
    });
  });
});
