import { Component, type ErrorInfo, type ReactNode } from 'react'

interface Props {
  children: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  }

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught error:', error, errorInfo)
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div className="mx-auto max-w-lg p-8 text-center space-y-4">
          <h2 className="text-h2 font-semibold text-alert">Something went wrong</h2>
          <p className="text-muted text-sm">{this.state.error?.message || 'Please try reloading the page.'}</p>
          <div className="flex justify-center gap-3">
            <button className="btn-primary" onClick={() => window.location.reload()}>
              Reload page
            </button>
            <a href="/" className="btn-secondary">
              Back to home
            </a>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
