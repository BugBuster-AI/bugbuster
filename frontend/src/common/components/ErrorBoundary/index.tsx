import { Alert } from 'antd'
import { Component, type ErrorInfo, type PropsWithChildren, type ReactNode } from 'react'

interface IState {
    hasError: boolean
    error: Error | null
}

interface IProps extends PropsWithChildren {
    fallback?: ReactNode
}

export class ErrorBoundary extends Component<IProps, IState> {
    state: IState = { hasError: false, error: null }

    static getDerivedStateFromError (error: Error): IState {
        return { hasError: true, error }
    }

    componentDidCatch (error: Error, info: ErrorInfo): void {
        console.error('ErrorBoundary caught:', error, info)
    }

    render (): ReactNode {
        if (this.state.hasError) {
            if (this.props.fallback) return this.props.fallback

            return (
                <Alert
                    description={ this.state.error?.message }
                    message="Something went wrong"
                    type="error"
                    showIcon
                />
            )
        }

        return this.props.children
    }
}
