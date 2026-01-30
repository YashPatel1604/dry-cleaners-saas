import React from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import RequireAuth from "./routes/RequireAuth";
import RequireTenant from "./routes/RequireTenant";
import AppShell from "./components/layout/AppShell";
import { Toaster } from "./components/ui/toaster";
import Login from "./pages/Login";
import SelectTenant from "./pages/SelectTenant";
import Orders from "./pages/Orders";
import OrderDetail from "./pages/OrderDetail";
import Customers from "./pages/Customers";
import CustomerDetail from "./pages/CustomerDetail";
import Inventory from "./pages/Inventory";
import Payments from "./pages/Payments";
import Reports from "./pages/Reports";
import Queue from "./pages/Queue";
import Invites from "./pages/Invites";
import Team from "./pages/Team";
import Audit from "./pages/Audit";
import Settings from "./pages/Settings";
import HomeDashboard from "./pages/HomeDashboard";
import DropLookup from "./pages/DropLookup";
import RegisterCustomer from "./pages/RegisterCustomer";
import Extras from "./pages/Extras";
import Admin from "./pages/Admin";

export default function App(): JSX.Element {
  return (
    <>
      <Routes>
        <Route path="/login" element={<Login />} />

        <Route element={<RequireAuth />}>
          <Route path="/select-tenant" element={<SelectTenant />} />

          <Route element={<RequireTenant />}>
            <Route element={<AppShell />}>
              <Route path="/home" element={<HomeDashboard />} />
              <Route path="/dashboard" element={<HomeDashboard />} />
              <Route path="/drop" element={<DropLookup />} />
              <Route path="/register" element={<RegisterCustomer />} />
              <Route path="/orders" element={<Orders />} />
              <Route path="/orders/:id" element={<OrderDetail />} />
              <Route path="/extras" element={<Extras />} />
              <Route path="/admin" element={<Admin />} />
              <Route path="/customers" element={<Customers />} />
              <Route path="/customers/:id" element={<CustomerDetail />} />
              <Route path="/inventory" element={<Inventory />} />
              <Route path="/payments" element={<Payments />} />
              <Route path="/reports" element={<Reports />} />
              <Route path="/queue" element={<Queue />} />
              <Route path="/invites" element={<Invites />} />
              <Route path="/team" element={<Team />} />
              <Route path="/audit" element={<Audit />} />
              <Route path="/settings" element={<Settings />} />
              <Route path="/" element={<Navigate to="/home" replace />} />
            </Route>
          </Route>
        </Route>
      </Routes>
      <Toaster />
    </>
  );
}
