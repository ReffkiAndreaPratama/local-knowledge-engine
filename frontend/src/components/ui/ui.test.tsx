import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { Badge, EmptyState, ErrorState, Modal, StatusDot, statusTone } from '@/components/ui'

describe('Badge', () => {
  it('renders its label', () => {
    render(<Badge tone="success">completed</Badge>)
    expect(screen.getByText('completed')).toBeInTheDocument()
  })
})

describe('statusTone', () => {
  it('maps statuses to badge tones', () => {
    expect(statusTone('completed')).toBe('success')
    expect(statusTone('failed')).toBe('danger')
    expect(statusTone('cancelled')).toBe('neutral')
    expect(statusTone('running')).toBe('warning')
  })
})

describe('StatusDot', () => {
  it('is hidden from assistive technology', () => {
    const { container } = render(<StatusDot status="completed" />)
    expect(container.querySelector('span')).toHaveAttribute('aria-hidden', 'true')
  })
})

describe('EmptyState', () => {
  it('shows title, description and action', () => {
    render(
      <EmptyState
        title="No documents"
        description="Import a file to begin"
        action={<button type="button">Import</button>}
      />,
    )
    expect(screen.getByText('No documents')).toBeInTheDocument()
    expect(screen.getByText('Import a file to begin')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Import' })).toBeInTheDocument()
  })
})

describe('ErrorState', () => {
  it('exposes the message as an alert and retries', () => {
    const onRetry = vi.fn()
    render(<ErrorState message="Backend unavailable" onRetry={onRetry} />)
    expect(screen.getByRole('alert')).toHaveTextContent('Backend unavailable')
    fireEvent.click(screen.getByRole('button', { name: 'Try again' }))
    expect(onRetry).toHaveBeenCalledTimes(1)
  })
})

describe('Modal', () => {
  it('renders a dialog and closes with the close button', () => {
    const onClose = vi.fn()
    render(
      <Modal open title="Remove document" onClose={onClose}>
        <p>Body text</p>
      </Modal>,
    )
    expect(screen.getByRole('dialog', { name: 'Remove document' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Close dialog' }))
    expect(onClose).toHaveBeenCalled()
  })

  it('does not render when closed', () => {
    render(
      <Modal open={false} title="Hidden" onClose={() => {}}>
        <p>Body text</p>
      </Modal>,
    )
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })
})
