import { Component, type ErrorInfo, type ReactNode } from "react";

type Props = {
  children: ReactNode;
};

type State = {
  hasError: boolean;
  errorMessage?: string;
};

class AppErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, errorMessage: undefined };

  static getDerivedStateFromError(error: unknown): State {
    const message =
      error instanceof Error
        ? error.message
        : typeof error === "string"
          ? error
          : "Unknown runtime error";

    return { hasError: true, errorMessage: message };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("Unhandled app error:", error, info);
    this.setState({ errorMessage: error.message || "Unknown runtime error" });
  }

  handleRetry = () => {
    this.setState({ hasError: false, errorMessage: undefined });
    window.location.reload();
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-[hsl(38_35%_92%)] flex items-center justify-center px-4">
          <div className="max-w-md rounded-2xl border border-red-200 bg-white p-6 text-center shadow-card">
            <h1 className="font-display text-2xl text-slate-900">Algo deu errado</h1>
            <p className="mt-2 font-body text-sm text-slate-600">
              Ocorreu um erro ao renderizar esta pagina. Atualize o navegador para tentar novamente.
            </p>
            {import.meta.env.DEV && this.state.errorMessage ? (
              <p className="mt-3 rounded-md bg-slate-100 px-3 py-2 font-mono text-xs text-slate-700">
                {this.state.errorMessage}
              </p>
            ) : null}
            <button
              type="button"
              onClick={this.handleRetry}
              className="mt-4 rounded-md bg-primary px-4 py-2 font-body text-sm text-primary-foreground hover:opacity-90"
            >
              Tentar novamente
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default AppErrorBoundary;
