import React from "react";
import { Navigate, Outlet } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";

export default function RequireAuth(): JSX.Element {
  const { isAuthenticated } = useAuth();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}
