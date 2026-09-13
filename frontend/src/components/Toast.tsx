import { useEffect } from "react";

interface ToastProps {
  message: string | null;
  onDismiss: () => void;
  variant: "error" | "info";
}

const AUTO_DISMISS_MS = 4000;

export function Toast({ message, onDismiss, variant }: ToastProps) {
  useEffect(() => {
    if (!message) return;
    const timer = setTimeout(onDismiss, AUTO_DISMISS_MS);
    return () => clearTimeout(timer);
  }, [message, onDismiss]);

  if (!message) return null;

  return (
    <div className={`toast toast-${variant}`} role="status">
      {message}
    </div>
  );
}
