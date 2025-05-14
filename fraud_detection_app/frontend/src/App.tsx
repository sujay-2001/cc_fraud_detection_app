import AppShell     from "./components/AppShell";
import PredictPage  from "./pages/PredictPage";
import MetricsPage  from "./pages/MetricsPage";
import ExplainPage  from "./pages/ExplainPage";
import LoginPage    from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import RequireAuth  from "./components/RequireAuth";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* public */}
        <Route path="/login"    element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />

        {/* protected app wrapper */}
        <Route
          path="/app/*"
          element={
            <RequireAuth>
              <AppShell />
            </RequireAuth>
          }
        >
          <Route path="predict" element={<PredictPage />} />
          <Route path="metrics" element={<MetricsPage />} />
          <Route path="explain" element={<ExplainPage />} />
          <Route index element={<Navigate to="predict" replace />} />
        </Route>

        {/* fallback */}
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
