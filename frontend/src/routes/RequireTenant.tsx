import React from "react";
import { Navigate, Outlet } from "react-router-dom";

import { useTenant } from "../tenant/TenantContext";

export default function RequireTenant(): JSX.Element {
  const { tenantSlug } = useTenant();

  if (!tenantSlug) {
    return <Navigate to="/select-tenant" replace />;
  }

  return <Outlet />;
}
