import { useState, useEffect } from "react";
import { api } from "../lib/api";
import { useNavigate, Link } from "react-router-dom";
import zxcvbn from "zxcvbn";

// --- utils --------------------------------------------------------------
const COUNTRIES = [
  "India",
  "United States",
  "United Kingdom",
  "Germany",
  "France",
  "Japan",
  "Australia",
  // … add full list or fetch dynamically
] as const;

const GENDERS = [
  { value: "Male", label: "Male" },
  { value: "Female", label: "Female" },
] as const;

export default function RegisterPage() {
  const nav = useNavigate();
  const [form, setForm] = useState({
    email: "",
    password: "",
    name: "",
    age: "",
    gender: "",
    country: "",
    otp: "",
  });

  const [passwordScore, setPasswordScore] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [otpSent, setOtpSent]   = useState(false);
  const [otpVerified, setOtpVerified] = useState(false);

  // ───────────────────────────────── password strength ─────────────────────────────────
  useEffect(() => {
    if (form.password) {
      const result = zxcvbn(form.password);
      setPasswordScore(result.score); // 0..4
    } else {
      setPasswordScore(null);
    }
  }, [form.password]);

  // ───────────────────────────────── handlers ─────────────────────────────────
  const onChange = (k: keyof typeof form) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
      setForm({ ...form, [k]: e.target.value });

  async function sendOtp() {
    try {
      await api.post("/auth/send-otp", { email: form.email });
      setOtpSent(true);
    } catch {
      setError("Failed to send OTP, try again");
    }
  }

  async function verifyOtp() {
    try {
      await api.post("/auth/verify-otp", { email: form.email, otp: form.otp });
      setOtpVerified(true);
    } catch {
      setError("Invalid OTP");
    }
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!otpVerified) return setError("Please verify email with OTP");
    if ((passwordScore ?? 0) < 2) return setError("Password too weak");

    setError(null);
    setLoading(true);
    try {
      await api.post("/auth/register", {
        email: form.email,
        password: form.password,
        name: form.name,
        age: Number(form.age) || null,
        gender: form.gender || null,
        country: form.country || null,
      });
      nav("/login", { state: { registered: true } });
    } catch (err: any) {
      setError(err.response?.data?.detail ?? "Registration failed");
    } finally {
      setLoading(false);
    }
  }

  // ───────────────────────────────── helpers ─────────────────────────────────
  const strengthBarClass = (() => {
    switch (passwordScore) {
      case 0:
      case 1:
        return "bg-risk-high"; // red (use palette red utility)
      case 2:
        return "bg-brand-blue";
      case 3:
      case 4:
        return "bg-brand-teal";
      default:
        return "bg-brand-gray-200";
    }
  })();

  return (
    <div className="flex h-full items-center justify-center bg-brand-gray-50 p-4">
      <form onSubmit={submit} className="ui-card w-full max-w-md space-y-3">
        <h1 className="text-xl font-semibold text-center text-brand-blue">
          Create account
        </h1>

        {/* name */}
        <input
          type="text"
          placeholder="Name"
          className="w-full rounded border border-brand-gray-200 p-2"
          value={form.name}
          onChange={onChange("name")}
          required
        />

        {/* age */}
        <input
          type="number"
          placeholder="Age"
          className="w-full rounded border border-brand-gray-200 p-2"
          value={form.age}
          onChange={onChange("age")}
        />

        {/* gender */}
        <div className="flex items-center gap-4">
          {GENDERS.map((g) => (
            <label key={g.value} className="flex items-center gap-1 text-sm text-brand-gray-700">
              <input
                type="radio"
                name="gender"
                value={g.value}
                checked={form.gender === g.value}
                onChange={onChange("gender")}
                className="accent-brand-blue"
              />
              {g.label}
            </label>
          ))}
        </div>

        {/* country */}
        <select
          value={form.country}
          onChange={onChange("country")}
          className="w-full rounded border border-brand-gray-200 p-2 bg-white text-brand-gray-800"
        >
          <option value="">Select country</option>
          {COUNTRIES.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>

        {/* email + OTP */}
        <div className="flex gap-2">
          <input
            type="email"
            placeholder="Email"
            className="flex-1 rounded border border-brand-gray-200 p-2"
            value={form.email}
            onChange={onChange("email")}
            required
          />
          <button
            type="button"
            disabled={!form.email || otpSent}
            onClick={sendOtp}
            className="rounded bg-brand-blue px-3 text-white hover:bg-brand-teal"
          >
            {otpSent ? "Sent" : "Send OTP"}
          </button>
        </div>
        {otpSent && !otpVerified && (
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="Enter OTP"
              className="flex-1 rounded border border-brand-gray-200 p-2"
              value={form.otp}
              onChange={onChange("otp")}
            />
            <button
              type="button"
              onClick={verifyOtp}
              className="rounded bg-brand-blue px-3 text-white hover:bg-brand-teal"
            >
              Verify
            </button>
          </div>
        )}
        {otpVerified && (
          <p className="text-sm text-brand-teal">Email verified ✓</p>
        )}

        {/* password */}
        <input
          type="password"
          placeholder="Password"
          className="w-full rounded border border-brand-gray-200 p-2"
          value={form.password}
          onChange={onChange("password")}
          required
        />
        {passwordScore !== null && (
          <div className="h-2 w-full rounded bg-brand-gray-200">
            <div
              className={`h-full rounded ${strengthBarClass}`}
              style={{ width: `${((passwordScore + 1) / 5) * 100}%` }}
            />
          </div>
        )}

        {error && <p className="text-sm text-center text-risk-high">{error}</p>}

        <button
          type="submit"
          disabled={loading || !otpVerified || (passwordScore ?? 0) < 2}
          className="w-full rounded bg-brand-blue py-2 font-medium text-white hover:bg-brand-teal disabled:opacity-60"
        >
          {loading ? "Creating…" : "Register"}
        </button>

        <p className="text-center text-sm">
          Have an account?
          <Link to="/login" className="text-brand-teal ml-1 hover:underline">
            Sign in
          </Link>
        </p>
      </form>
    </div>
  );
}
