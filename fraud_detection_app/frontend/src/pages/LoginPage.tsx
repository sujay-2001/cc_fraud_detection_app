import { useState } from "react";
import { api } from "../lib/api";
import { useNavigate, Link } from "react-router-dom";

export default function LoginPage() {
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const { data } = await api.post("/auth/login", { email, password });
      localStorage.setItem("fraud_token", data.access_token);
      nav("/app/predict");
    } catch (err: any) {
      // backend returns {detail: "..."} on error (FastAPI default)
      const detail = err.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex h-full items-center justify-center bg-brand-gray-50 p-4">
      <form
        onSubmit={handleSubmit}
        className="ui-card w-full max-w-sm space-y-4"
      >
        <h1 className="text-xl font-semibold text-center text-brand-blue">
          Sign in
        </h1>

        <input
          type="email"
          placeholder="email@example.com"
          className="w-full rounded border border-brand-gray-200 p-2"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />

        <input
          type="password"
          placeholder="password"
          className="w-full rounded border border-brand-gray-200 p-2"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />

        {error && (
          <p className="text-sm text-center text-risk-high">{error}</p>
        )}

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded bg-brand-blue py-2 font-medium text-white hover:bg-brand-teal"
        >
          {loading ? "Signing in…" : "Login"}
        </button>

        <p className="text-center text-sm">
          New here?{" "}
          <Link to="/register" className="text-brand-teal hover:underline">
            Create an account
          </Link>
        </p>
      </form>
    </div>
  );
}
