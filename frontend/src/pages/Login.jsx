import React, { useState } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { devSeedAccounts } from "../services/api";
import cardiacLogo from "../assets/cardiac_logo.png";
import cardiacHero from "../assets/cardiac_heart_hero.png";
import "./Login.css";

/* --- Scientific & Medical UI Icons (Inline SVGs) --- */
const BarChartIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="18" y1="20" x2="18" y2="10" />
    <line x1="12" y1="20" x2="12" y2="4" />
    <line x1="6" y1="20" x2="6" y2="14" />
  </svg>
);

const LineChartIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
  </svg>
);

const DocumentIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
    <polyline points="14 2 14 8 20 8" />
    <line x1="16" y1="13" x2="8" y2="13" />
    <line x1="16" y1="17" x2="8" y2="17" />
    <polyline points="10 9 9 9 8 9" />
  </svg>
);

const AlertTriangleIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
    <line x1="12" y1="9" x2="12" y2="13" />
    <line x1="12" y1="17" x2="12.01" y2="17" />
  </svg>
);

const MailIcon = ({ size = 16 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
    <polyline points="22,6 12,13 2,6" />
  </svg>
);

const LockIcon = ({ size = 16 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
    <path d="M7 11V7a5 5 0 0 1 10 0v4" />
  </svg>
);

const EyeIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
    <circle cx="12" cy="12" r="3" />
  </svg>
);

const EyeOffIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
    <line x1="1" y1="1" x2="23" y2="23" />
  </svg>
);

const SignInIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4" />
    <polyline points="10 17 15 12 10 7" />
    <line x1="15" y1="12" x2="3" y2="12" />
  </svg>
);

const FlaskIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M10 2v7.527a2 2 0 0 1-.211.896L4.72 20.55a1 1 0 0 0 .9 1.45h12.76a1 1 0 0 0 .9-1.45l-5.069-10.127A2 2 0 0 1 14 9.527V2" />
    <line x1="8.5" y1="2" x2="15.5" y2="2" />
    <line x1="7" y1="16" x2="17" y2="16" />
  </svg>
);

const SearchIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="11" cy="11" r="8" />
    <line x1="21" y1="21" x2="16.65" y2="16.65" />
  </svg>
);

const ShieldIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
  </svg>
);

const ChevronRightIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="9 18 15 12 9 6" />
  </svg>
);

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [demoNotice, setDemoNotice] = useState(null);

  const redirectPath = location.state?.from?.pathname || "/";

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email.trim() || !password) {
      setError("Please provide both email and password.");
      return;
    }

    setLoading(true);
    setError(null);
    try {
      await login(email.trim(), password);
      navigate(redirectPath, { replace: true });
    } catch (err) {
      setError(err.message || "Failed to log in. Please check your credentials.");
    } finally {
      setLoading(false);
    }
  };

  const fillQuickDemo = async (demoEmail, demoPassword) => {
    setEmail(demoEmail);
    setPassword(demoPassword);
    setError(null);
    setDemoNotice(`Pre-filled credentials for ${demoEmail}. Click "Sign In" to proceed.`);
    // Proactively seed dev accounts if they haven't been created yet
    try {
      await devSeedAccounts();
    } catch (_) {}
  };

  const handleForgotPassword = (e) => {
    e.preventDefault();
    setError(null);
    setDemoNotice(
      "In this research environment, credentials are reset by your workspace administrator or pre-filled via Quick Demo Logins below."
    );
  };

  return (
    <div className="cdl-login-page">
      {/* ====================================================================
          LEFT SIDE: Research Branding, Hero Visualization & Feature Highlights
          ==================================================================== */}
      <section className="cdl-left-panel" aria-label="Cardiac Deformation Lab Research Information">
        {/* Subtle Background Mesh & Light Gradients */}
        <div className="cdl-grid-bg" aria-hidden="true" />
        <div className="cdl-ambient-glow-1" aria-hidden="true" />
        <div className="cdl-ambient-glow-2" aria-hidden="true" />

        {/* Background EKG Sine Wave Curve */}
        <svg
          className="cdl-ekg-svg-bg"
          viewBox="0 0 500 150"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          aria-hidden="true"
        >
          <path
            d="M0,75 L120,75 L135,75 L145,45 L155,105 L165,25 L175,120 L185,65 L195,85 L205,75 L500,75"
            stroke="#38bdf8"
            strokeWidth="3"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <path
            d="M0,75 Q125,20 250,75 T500,75"
            stroke="rgba(56, 189, 248, 0.25)"
            strokeWidth="1.5"
            strokeDasharray="4 4"
          />
        </svg>

        {/* Central Anatomical Cardiac Mesh Visualization */}
        <div className="cdl-heart-vis-container" aria-hidden="true">
          <img
            src={cardiacHero}
            alt="3D Cardiac Deformation Mesh Visualization"
            className="cdl-heart-vis-img"
          />
        </div>

        {/* Top Header Branding */}
        <header className="cdl-left-header">
          <div className="cdl-brand-badge-row">
            <img src={cardiacLogo} alt="Cardiac Deformation Lab Icon" className="cdl-header-logo-icon" />
            <div className="cdl-header-titles">
              <h1 className="cdl-header-title">Cardiac Deformation Lab</h1>
              <p className="cdl-header-tagline">Research Workspace</p>
            </div>
          </div>
          <p className="cdl-header-desc">
            A computational research workspace for cardiac deformation analysis, visualization, and benchmarking.
          </p>
        </header>

        {/* 3 Vertical Feature Cards */}
        <div className="cdl-features-column">
          <div className="cdl-feature-card">
            <div className="cdl-feature-icon-box" aria-hidden="true">
              <BarChartIcon />
            </div>
            <div className="cdl-feature-texts">
              <h3 className="cdl-feature-title">Analyze</h3>
              <p className="cdl-feature-desc">Cardiac deformation metrics</p>
            </div>
          </div>

          <div className="cdl-feature-card">
            <div className="cdl-feature-icon-box" aria-hidden="true">
              <LineChartIcon />
            </div>
            <div className="cdl-feature-texts">
              <h3 className="cdl-feature-title">Visualize</h3>
              <p className="cdl-feature-desc">Advanced 3D &amp; 2D analysis</p>
            </div>
          </div>

          <div className="cdl-feature-card">
            <div className="cdl-feature-icon-box" aria-hidden="true">
              <DocumentIcon />
            </div>
            <div className="cdl-feature-texts">
              <h3 className="cdl-feature-title">Research</h3>
              <p className="cdl-feature-desc">Access studies and benchmarks</p>
            </div>
          </div>
        </div>

        {/* Bottom Research Prototype Disclaimer */}
        <div className="cdl-prototype-card" role="note">
          <div className="cdl-warning-badge" aria-hidden="true">
            <AlertTriangleIcon />
          </div>
          <div className="cdl-prototype-texts">
            <h4 className="cdl-prototype-title">Research Prototype</h4>
            <p className="cdl-prototype-desc">
              Computational research workspace only. Not for clinical diagnostics or hospital patient record storage.
            </p>
          </div>
        </div>
      </section>

      {/* ====================================================================
          RIGHT SIDE: Modern White Login Card & Access Controls
          ==================================================================== */}
      <main className="cdl-right-panel" aria-label="Sign In Area">
        {/* Soft Background Pastels */}
        <div className="cdl-light-blob-top" aria-hidden="true" />
        <div className="cdl-light-blob-bottom" aria-hidden="true" />

        {/* Floating White Login Card */}
        <div className="cdl-login-card-container">
          {/* Card Header Branding */}
          <div className="cdl-card-header">
            <img src={cardiacLogo} alt="Cardiac Deformation Lab Logo" className="cdl-card-logo" />
            <h2 className="cdl-card-title">Cardiac Deformation Lab</h2>
            <p className="cdl-card-subtitle">Research Workspace</p>
            <p className="cdl-card-desc">
              Sign in to access your studies, deformation analyses, and reference benchmarks.
            </p>
          </div>

          {/* Error Banner */}
          {error && (
            <div className="cdl-alert-banner cdl-alert-error" role="alert">
              <span>⚠️</span>
              <div>{error}</div>
            </div>
          )}

          {/* Demo Info Banner */}
          {demoNotice && (
            <div className="cdl-alert-banner cdl-alert-info" role="status">
              <span>💡</span>
              <div>{demoNotice}</div>
            </div>
          )}

          {/* Login Form */}
          <form onSubmit={handleSubmit} className="cdl-form" noValidate>
            {/* Email Field */}
            <div className="cdl-field-group">
              <label htmlFor="login-email" className="cdl-label">
                <span className="cdl-label-icon"><MailIcon size={14} /></span>
                Email Address
              </label>
              <div className="cdl-input-wrapper">
                <span className="cdl-input-icon">
                  <MailIcon size={16} />
                </span>
                <input
                  id="login-email"
                  type="email"
                  className={`cdl-input ${email ? "has-value" : ""}`}
                  placeholder="admin@cardiaclab.local"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={loading}
                  required
                  autoFocus
                  autoComplete="email"
                />
              </div>
            </div>

            {/* Password Field */}
            <div className="cdl-field-group">
              <label htmlFor="login-password" className="cdl-label">
                <span className="cdl-label-icon"><LockIcon size={14} /></span>
                Password
              </label>
              <div className="cdl-input-wrapper">
                <span className="cdl-input-icon">
                  <LockIcon size={16} />
                </span>
                <input
                  id="login-password"
                  type={showPassword ? "text" : "password"}
                  className="cdl-input"
                  placeholder="••••••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={loading}
                  required
                  autoComplete="current-password"
                />
                <button
                  type="button"
                  className="cdl-password-toggle"
                  onClick={() => setShowPassword(!showPassword)}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  title={showPassword ? "Hide password" : "Show password"}
                  tabIndex={-1}
                >
                  {showPassword ? <EyeOffIcon /> : <EyeIcon />}
                </button>
              </div>
            </div>

            {/* Remember Me & Forgot Password Row */}
            <div className="cdl-form-helper-row">
              <label className="cdl-checkbox-label">
                <input
                  type="checkbox"
                  className="cdl-checkbox-custom"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                />
                <span>Remember me</span>
              </label>

              <button
                type="button"
                className="cdl-forgot-btn"
                onClick={handleForgotPassword}
              >
                Forgot password?
              </button>
            </div>

            {/* Sign In Button */}
            <button
              type="submit"
              className="cdl-submit-btn"
              disabled={loading}
            >
              <SignInIcon />
              <span>{loading ? "Authenticating..." : "Sign In to Workspace"}</span>
            </button>
          </form>

          {/* OR Divider */}
          <div className="cdl-divider-row" aria-hidden="true">
            <span className="cdl-divider-line" />
            <span className="cdl-divider-text">OR</span>
            <span className="cdl-divider-line" />
          </div>

          {/* Quick Demo Credentials (Development) */}
          <div className="cdl-demo-section">
            <div className="cdl-demo-title">Quick Demo Logins (Development)</div>
            <div className="cdl-demo-grid">
              <button
                type="button"
                className="cdl-demo-btn researcher"
                onClick={() => fillQuickDemo("demo@cardiaclab.local", "DemoResearcher123!")}
                title="Log in as Demo Researcher"
              >
                <FlaskIcon />
                <span>Demo Researcher</span>
              </button>
              <button
                type="button"
                className="cdl-demo-btn reviewer"
                onClick={() => fillQuickDemo("reviewer@cardiaclab.local", "ReviewerPass123!")}
                title="Log in as Peer Reviewer"
              >
                <SearchIcon />
                <span>Reviewer</span>
              </button>
              <button
                type="button"
                className="cdl-demo-btn admin"
                onClick={() => fillQuickDemo("admin@cardiaclab.local", "AdminPass123!")}
                title="Log in as System Admin"
              >
                <ShieldIcon />
                <span>Admin</span>
              </button>
            </div>
          </div>

          {/* Footer Registration Link */}
          <div className="cdl-card-footer">
            <span>Need an account?</span>
            <Link to="/register">
              <span>Create Account</span>
              <ChevronRightIcon />
            </Link>
          </div>
        </div>
      </main>
    </div>
  );
}
