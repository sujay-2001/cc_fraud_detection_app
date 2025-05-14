import { Navigate } from "react-router-dom";

export default function RequireAuth({ children }: { children: JSX.Element }) {
  const token = localStorage.getItem("fraud_token");
  return token ? children : <Navigate to="/login" replace />;
}
