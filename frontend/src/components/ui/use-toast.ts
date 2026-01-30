import * as React from "react";

import type { ToastVariant } from "./toast";

export type ToastMessage = {
  id: string;
  title?: React.ReactNode;
  description?: React.ReactNode;
  variant?: ToastVariant;
  duration?: number;
};

type ToastState = {
  toasts: ToastMessage[];
};

type ToastAction =
  | { type: "ADD_TOAST"; toast: ToastMessage }
  | { type: "DISMISS_TOAST"; toastId?: string };

const listeners = new Set<(state: ToastState) => void>();
let memoryState: ToastState = { toasts: [] };
const toastTimeouts = new Map<string, number>();

function dispatch(action: ToastAction) {
  switch (action.type) {
    case "ADD_TOAST": {
      memoryState = {
        ...memoryState,
        toasts: [action.toast, ...memoryState.toasts].slice(0, 3),
      };
      break;
    }
    case "DISMISS_TOAST": {
      const { toastId } = action;
      memoryState = {
        ...memoryState,
        toasts: toastId
          ? memoryState.toasts.filter((t) => t.id !== toastId)
          : [],
      };
      break;
    }
    default:
      break;
  }
  listeners.forEach((listener) => listener(memoryState));
}

function scheduleDismiss(id: string, duration = 4000) {
  if (toastTimeouts.has(id)) return;
  const timeout = window.setTimeout(() => {
    toastTimeouts.delete(id);
    dispatch({ type: "DISMISS_TOAST", toastId: id });
  }, duration);
  toastTimeouts.set(id, timeout);
}

export function toast(input: Omit<ToastMessage, "id">) {
  const id = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  const toastMessage: ToastMessage = { id, ...input };
  dispatch({ type: "ADD_TOAST", toast: toastMessage });
  scheduleDismiss(id, toastMessage.duration);
  return { id };
}

export function dismiss(toastId?: string) {
  if (toastId) {
    const timeout = toastTimeouts.get(toastId);
    if (timeout) {
      window.clearTimeout(timeout);
      toastTimeouts.delete(toastId);
    }
  } else {
    toastTimeouts.forEach((timeout) => window.clearTimeout(timeout));
    toastTimeouts.clear();
  }
  dispatch({ type: "DISMISS_TOAST", toastId });
}

export function useToast() {
  const [state, setState] = React.useState<ToastState>(memoryState);

  React.useEffect(() => {
    listeners.add(setState);
    return () => {
      listeners.delete(setState);
    };
  }, []);

  return {
    ...state,
    toast,
    dismiss,
  };
}
