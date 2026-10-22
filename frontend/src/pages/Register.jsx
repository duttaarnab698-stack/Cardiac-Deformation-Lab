import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import cardiacLogo from "../assets/cardiac_logo.png";
import cardiacHero from "../assets/cardiac_heart_hero.png";
import "./Register.css";

/* --- Scientific & Medical UI Icons (Inline SVGs) --- */
const BarChartIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="18" y1="20" x2="18" y2="10" />
    <line x1="12" y1="20" x2="12" y2="4" />
    <line x1="6" y1="20" x2="6" y2="14" />
  </svg>
);

const CubeIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
    <polyline points="3.27 6.96 12 12.01 20.73 6.96" />
    <line x1="12" y1="22.08" x2="12" y2="12" />
  </svg>
);

const CollaborateIcon = () => (
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

const FlaskIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M10 2v7.527a2 2 0 0 1-.211.896L4.72 20.55a1 1 0 0 0 .9 1.45h12.76a1 1 0 0 0 .9-1.45l-5.069-10.127A2 2 0 0 1 14 9.527V2" />
    <line x1="8.5" y1="2" x2="15.5" y2="2" />
    <line x1="7" y1="16" x2="17" y2="16" />
  </svg>
);

const UserIcon = ({ size = 16 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
    <circle cx="12" cy="7" r="4" />
  </svg>
);

const MailIcon = ({ size = 16 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
    <polyline points="22,6 12,13 2,6" />
  </svg>
);

const TeamIcon = ({ size = 16 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
    <circle cx="9" cy="7" r="4" />
    <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
    <path d="M16 3.13a4 4 0 0 1 0 7.75" />
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

const UserPlusIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
    <circle cx="8.5" cy="7" r="4" />
    <line x1="20" y1="8" x2="20" y2="14" />
    <line x1="23" y1="11" x2="17" y2="11" />
  </svg>
);

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [role, setRole] = useState("researcher");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSuccessMsg(null);

    // Validation
    if (!name.trim()) {
      setError("Please enter your name or researcher identifier.");
      return;
    }

    if (!email.trim() || !email.includes("@")) {
      setError("Please enter a valid email address.");
      return;
    }

    if (password.length < 8) {
      setError("Password must be at least 8 characters long.");
      return;
    }

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setLoading(true);
    try {
      await register(name.trim(), email.trim(), password, role);
      setSuccessMsg("Account registered successfully! Redirecting to login...");
      setTimeout(() => {
        navigate("/login");
      }, 1500);
    } catch (err) {
      setError(err.message || "Registration failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="cdl-reg-page">
      {/* ====================================================================
          LEFT SIDE: Research Branding, Hero Visualization & Feature Highlights
          ==================================================================== */}
      <section className="cdl-reg-left-panel" aria-label="Cardiac Deformation Lab Registration Information">
        {/* Subtle Background Mesh & Light Gradients */}
        <div className="cdl-reg-grid-bg" aria-hidden="true" />
        <div className="cdl-reg-ambient-glow-1" aria-hidden="true" />
        <div className="cdl-reg-ambient-glow-2" aria-hidden="true" />

        {/* Background EKG Sine Wave Curve */}
        <svg
          className="cdl-reg-ekg-svg-bg"
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
        <div className="cdl-reg-heart-vis-container" aria-hidden="true">
          <img
            src={cardiacHero}
            alt="3D Cardiac Deformation Mesh Visualization"
            className="cdl-reg-heart-vis-img"
          />
        </div>

        {/* Top Header Branding */}
        <header className="cdl-reg-left-header">
          <div className="cdl-reg-brand-badge-row">
            <img src={cardiacLogo} alt="Cardiac Deformation Lab Icon" className="cdl-reg-header-logo-icon" />
            <div className="cdl-reg-header-titles">
              <h1 className="cdl-reg-header-title">Cardiac Deformation Lab</h1>
              <p className="cdl-reg-header-tagline">Research Workspace</p>
            </div>
          </div>
          <p className="cdl-reg-header-desc">
            A computational research workspace for cardiac deformation analysis, visualization and benchmarking.
          </p>
        </header>

        {/* 3 Vertical Feature Cards */}
        <div className="cdl-reg-features-column">
          <div className="cdl-reg-feature-card">
            <div className="cdl-reg-feature-icon-box blue" aria-hidden="true">
              <BarChartIcon />
            </div>
            <div className="cdl-reg-feature-texts">
              <h3 className="cdl-reg-feature-title">Organize Research</h3>
              <p className="cdl-reg-feature-desc">Manage studies, datasets and results</p>
            </div>
          </div>

          <div className="cdl-reg-feature-card">
            <div className="cdl-reg-feature-icon-box purple" aria-hidden="true">
              <CubeIcon />
            </div>
            <div className="cdl-reg-feature-texts">
              <h3 className="cdl-reg-feature-title">Analyze Deformation</h3>
              <p className="cdl-reg-feature-desc">Advanced 2D &amp; 3D visualization tools</p>
            </div>
          </div>

          <div className="cdl-reg-feature-card">
            <div className="cdl-reg-feature-icon-box green" aria-hidden="true">
              <CollaborateIcon />
            </div>
            <div className="cdl-reg-feature-texts">
              <h3 className="cdl-reg-feature-title">Collaborate</h3>
              <p className="cdl-reg-feature-desc">Work with researchers and reviewers</p>
            </div>
          </div>
        </div>

        {/* Bottom Research Prototype Disclaimer */}
        <div className="cdl-reg-prototype-card" role="note">
          <div className="cdl-reg-warning-badge" aria-hidden="true">
            <AlertTriangleIcon />
          </div>
          <div className="cdl-reg-prototype-texts">
            <h4 className="cdl-reg-prototype-title">Research Prototype</h4>
            <p className="cdl-reg-prototype-desc">
              For experimental motion analysis only. No clinical or PHI data is permitted.
            </p>
          </div>
        </div>
      </section>

      {/* ====================================================================
          RIGHT SIDE: Modern White Registration Card
          ==================================================================== */}
      <main className="cdl-reg-right-panel" aria-label="Registration Area">
        {/* Soft Background Pastels */}
        <div className="cdl-reg-light-blob-top" aria-hidden="true" />
        <div className="cdl-reg-light-blob-bottom" aria-hidden="true" />

        {/* Floating White Registration Card */}
        <div className="cdl-reg-card-container">
          {/* Card Header Branding */}
          <div className="cdl-reg-card-header">
            <img src={cardiacLogo} alt="Cardiac Deformation Lab Logo" className="cdl-reg-card-logo" />
            <h2 className="cdl-reg-card-title">Create Research Account</h2>
            <p className="cdl-reg-card-subtitle">Workspace Registration</p>
            <p className="cdl-reg-card-desc">
              Join the Cardiac Deformation Lab to organize studies and run quantitative analyses.
            </p>
          </div>

          {/* Research Prototype Notice Banner */}
          <div className="cdl-reg-notice-banner" role="note">
            <div className="cdl-reg-notice-icon-badge" aria-hidden="true">
              <FlaskIcon />
            </div>
            <div className="cdl-reg-notice-content">
              <strong className="cdl-reg-notice-title">Research Prototype Notice:</strong>
              For experimental motion analysis only. No clinical or PHI data is permitted.
            </div>
          </div>

          {/* Error Banner */}
          {error && (
            <div className="cdl-reg-alert-banner cdl-reg-alert-error" role="alert">
              <span>⚠️</span>
              <div>{error}</div>
            </div>
          )}

          {/* Success Banner */}
          {successMsg && (
            <div className="cdl-reg-alert-banner cdl-reg-alert-success" role="status">
              <span>✅</span>
              <div>{successMsg}</div>
            </div>
          )}

          {/* Registration Form */}
          <form onSubmit={handleSubmit} className="cdl-reg-form" noValidate>
            {/* Full Name */}
            <div className="cdl-reg-field-group">
              <label htmlFor="reg-name" className="cdl-reg-label">
                <span className="cdl-reg-label-icon"><UserIcon size={14} /></span>
                Full Name / Researcher Name
              </label>
              <div className="cdl-reg-input-wrapper">
                <span className="cdl-reg-input-icon">
                  <UserIcon size={16} />
                </span>
                <input
                  id="reg-name"
                  type="text"
                  className={`cdl-reg-input ${name ? "has-value" : ""}`}
                  placeholder="Dr. Jane Doe"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  disabled={loading}
                  required
                  autoFocus
                  autoComplete="name"
                />
              </div>
            </div>

            {/* Email Address */}
            <div className="cdl-reg-field-group">
              <label htmlFor="reg-email" className="cdl-reg-label">
                <span className="cdl-reg-label-icon"><MailIcon size={14} /></span>
                Email Address
              </label>
              <div className="cdl-reg-input-wrapper">
                <span className="cdl-reg-input-icon">
                  <MailIcon size={16} />
                </span>
                <input
                  id="reg-email"
                  type="email"
                  className={`cdl-reg-input ${email ? "has-value" : ""}`}
                  placeholder="admin@cardiaclab.local"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={loading}
                  required
                  autoComplete="email"
                />
              </div>
            </div>

            {/* Role Selection */}
            <div className="cdl-reg-field-group">
              <label htmlFor="reg-role" className="cdl-reg-label">
                <span className="cdl-reg-label-icon"><TeamIcon size={14} /></span>
                Role
              </label>
              <select
                id="reg-role"
                className="cdl-reg-select"
                value={role}
                onChange={(e) => setRole(e.target.value)}
                disabled={loading}
              >
                <option value="researcher">Researcher (Default — create &amp; manage studies)</option>
                <option value="reviewer">Reviewer (Read-only review of shared studies)</option>
              </select>
            </div>

            {/* Password & Confirm Password (Side-by-side on desktop, stacked on mobile) */}
            <div className="cdl-reg-passwords-row">
              {/* Password */}
              <div className="cdl-reg-field-group">
                <label htmlFor="reg-password" className="cdl-reg-label">
                  <span className="cdl-reg-label-icon"><LockIcon size={14} /></span>
                  Password (Minimum 8 characters)
                </label>
                <div className="cdl-reg-input-wrapper">
                  <input
                    id="reg-password"
                    type={showPassword ? "text" : "password"}
                    className="cdl-reg-input"
                    placeholder="••••••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    disabled={loading}
                    required
                    autoComplete="new-password"
                  />
                  <button
                    type="button"
                    className="cdl-reg-password-toggle"
                    onClick={() => setShowPassword(!showPassword)}
                    aria-label={showPassword ? "Hide password" : "Show password"}
                    title={showPassword ? "Hide password" : "Show password"}
                    tabIndex={-1}
                  >
                    {showPassword ? <EyeOffIcon /> : <EyeIcon />}
                  </button>
                </div>
              </div>

              {/* Confirm Password */}
              <div className="cdl-reg-field-group">
                <label htmlFor="reg-confirm" className="cdl-reg-label">
                  <span className="cdl-reg-label-icon"><LockIcon size={14} /></span>
                  Confirm Password
                </label>
                <div className="cdl-reg-input-wrapper">
                  <input
                    id="reg-confirm"
                    type={showConfirmPassword ? "text" : "password"}
                    className="cdl-reg-input"
                    placeholder="••••••••••••"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    disabled={loading}
                    required
                    autoComplete="new-password"
                  />
                  <button
                    type="button"
                    className="cdl-reg-password-toggle"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    aria-label={showConfirmPassword ? "Hide confirm password" : "Show confirm password"}
                    title={showConfirmPassword ? "Hide confirm password" : "Show confirm password"}
                    tabIndex={-1}
                  >
                    {showConfirmPassword ? <EyeOffIcon /> : <EyeIcon />}
                  </button>
                </div>
              </div>
            </div>

            {/* Register Account Button */}
            <button
              type="submit"
              className="cdl-reg-submit-btn"
              disabled={loading}
            >
              <UserPlusIcon />
              <span>{loading ? "Creating Account..." : "Register Account"}</span>
            </button>
          </form>

          {/* OR Divider */}
          <div className="cdl-reg-divider-row" aria-hidden="true">
            <span className="cdl-reg-divider-line" />
            <span className="cdl-reg-divider-text">OR</span>
            <span className="cdl-reg-divider-line" />
          </div>

          {/* Bottom Footer Navigation */}
          <div className="cdl-reg-card-footer">
            <span>Already have an account?</span>
            <Link to="/login">Sign In</Link>
          </div>
        </div>
      </main>
    </div>
  );
}
