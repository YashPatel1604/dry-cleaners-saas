import { useEffect } from "react";

type Handler = () => void;

export function useAuthEvents(onUnauthorized: Handler, onForbidden?: Handler): void {
  useEffect(() => {
    const handleUnauthorized = () => {
      onUnauthorized();
    };

    const handleForbidden = () => {
      if (onForbidden) {
        onForbidden();
      }
    };

    window.addEventListener("auth:unauthorized", handleUnauthorized);
    window.addEventListener("auth:forbidden", handleForbidden);

    return () => {
      window.removeEventListener("auth:unauthorized", handleUnauthorized);
      window.removeEventListener("auth:forbidden", handleForbidden);
    };
  }, [onUnauthorized, onForbidden]);
}
