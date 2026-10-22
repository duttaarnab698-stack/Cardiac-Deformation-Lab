import { useState } from "react";
import { Link } from "react-router-dom";
import { useAnalysis } from "../context/AnalysisContext";
import { useAuth } from "../context/AuthContext";
import { API_BASE_URL, devSeedAccounts } from "../services/api";
import "./Settings.css";

export default function Settings() {
  const {
    theme,
    toggleTheme,
    setTheme,
    clearResults,
    latestAnalysisResult,
    latestTemporalResult,
  } = useAnalysis();
  const { user, isAdmin, isReviewer } = useAuth();

  // Navigation category state
  const [activeCategory, setActiveCategory] = useState("all");

  // Dev account seeding state
  const [seedMsg, setSeedMsg] = useState(null);
  const [seeding, setSeeding] = useState(false);

  // Cache clear feedback state
  const [cacheClearedMsg, setCacheClearedMsg] = useState(false);

  // Copy feedback state
  const [copiedKey, setCopiedKey] = useState(null);

  const handleDevSeed = async () => {
    try {
      setSeeding(true);
      setSeedMsg(null);
      const res = await devSeedAccounts();
      setSeedMsg({
        type: "success",
        text: res.message || "Development accounts seeded successfully.",
      });
    } catch (err) {
      setSeedMsg({
        type: "error",
        text: err.message || "Failed to seed development accounts.",
      });
    } finally {
      setSeeding(false);
    }
  };

  const handleClearCache = () => {
    clearResults();
    setCacheClearedMsg(true);
    setTimeout(() => setCacheClearedMsg(false), 3000);
  };

  const handleCopyEndpoint = (text, key) => {
    if (!text) return;
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const hasCachedData = Boolean(latestAnalysisResult || latestTemporalResult);

  return (
    <div className="cdl-set-page">
      {/* 1. Header & Breadcrumbs */}
      <div className="cdl-set-header-wrap">
        <div className="cdl-set-title-area">
          <nav className="cdl-set-breadcrumb" aria-label="Breadcrumb">
            <Link to="/" className="bc-link">
              <span>Home</span>
            </Link>
            <span className="bc-sep">/</span>
            <span className="bc-link">Workspace</span>
            <span className="bc-sep">/</span>
            <span className="bc-current">Settings &amp; Configuration</span>
          </nav>

          <div className="cdl-set-pill-row">
            <span className="cdl-set-badge cdl-set-badge-primary">
              System Configuration
            </span>
            <span className="cdl-set-badge cdl-set-badge-cyan">
              FastAPI Engine
            </span>
            <span className="cdl-set-badge cdl-set-badge-purple">
              Theme: {theme.toUpperCase()}
            </span>
          </div>

          <h1 className="cdl-set-title">
            <span className="icon-accent">⚙️</span>
            Workspace Settings
          </h1>
          <p className="cdl-set-subtitle">
            Manage your research workspace preferences, account configuration,
            visualization themes, API connectivity, and session telemetry.
          </p>
        </div>
      </div>

      {/* 2. Two-Column Workspace Layout */}
      <div className="cdl-set-layout">
        {/* ==================================================================
            LEFT COLUMN: SETTINGS CATEGORY NAVIGATION
            ================================================================== */}
        <aside className="cdl-set-nav" aria-label="Settings Categories">
          <div className="cdl-set-nav-header">Settings Categories</div>

          <button
            type="button"
            className={`cdl-set-nav-btn ${activeCategory === "all" ? "is-active" : ""}`}
            onClick={() => setActiveCategory("all")}
          >
            <span className="cdl-set-nav-icon">📋</span>
            <span>All Settings</span>
          </button>

          <button
            type="button"
            className={`cdl-set-nav-btn ${activeCategory === "account" ? "is-active" : ""}`}
            onClick={() => setActiveCategory("account")}
          >
            <span className="cdl-set-nav-icon">👤</span>
            <span>Account &amp; Workspace</span>
          </button>

          <button
            type="button"
            className={`cdl-set-nav-btn ${activeCategory === "appearance" ? "is-active" : ""}`}
            onClick={() => setActiveCategory("appearance")}
          >
            <span className="cdl-set-nav-icon">🎨</span>
            <span>Appearance &amp; Display</span>
          </button>

          <button
            type="button"
            className={`cdl-set-nav-btn ${activeCategory === "api" ? "is-active" : ""}`}
            onClick={() => setActiveCategory("api")}
          >
            <span className="cdl-set-nav-icon">🔌</span>
            <span>API &amp; Connectivity</span>
          </button>

          <button
            type="button"
            className={`cdl-set-nav-btn ${activeCategory === "cache" ? "is-active" : ""}`}
            onClick={() => setActiveCategory("cache")}
          >
            <span className="cdl-set-nav-icon">💾</span>
            <span>Session &amp; Data Cache</span>
          </button>

          <button
            type="button"
            className={`cdl-set-nav-btn ${activeCategory === "about" ? "is-active" : ""}`}
            onClick={() => setActiveCategory("about")}
          >
            <span className="cdl-set-nav-icon">ℹ️</span>
            <span>Architecture &amp; Notice</span>
          </button>
        </aside>

        {/* ==================================================================
            RIGHT COLUMN: SETTINGS CONTENT CARDS
            ================================================================== */}
        <main className="cdl-set-content">
          {/* Card 1: User Account & Workspace Settings */}
          {(activeCategory === "all" || activeCategory === "account") && (
            <section className="cdl-set-card" aria-labelledby="card-account-title">
              <div className="cdl-set-card-header">
                <h2 id="card-account-title" className="cdl-set-card-title">
                  <span>👤</span>
                  <span>Research Workspace &amp; Identity</span>
                </h2>
                {user && (
                  <span
                    className={`cdl-set-role-badge ${user.role || "researcher"}`}
                  >
                    {(user.role || "researcher").toUpperCase()}
                  </span>
                )}
              </div>

              <div className="cdl-set-card-body">
                {user ? (
                  <>
                    {/* Logged in User */}
                    <div className="cdl-set-row">
                      <div className="cdl-set-row-info">
                        <span className="cdl-set-name">Logged-in Researcher</span>
                        <p className="cdl-set-desc">{user.email}</p>
                      </div>
                      <span className="cdl-set-badge-val">
                        {user.name || "Unnamed Researcher"}
                      </span>
                    </div>

                    {/* Workspace Role */}
                    <div className="cdl-set-row">
                      <div className="cdl-set-row-info">
                        <span className="cdl-set-name">Access Authorization</span>
                        <p className="cdl-set-desc">
                          {isAdmin
                            ? "Full administrative governance: manage user roles, audit workspace activity, and oversee all studies."
                            : isReviewer
                            ? "Read-only inspection access across studies, kinematics, and publication reports."
                            : "Primary investigator access: execute optical flow analyses, track ROIs, and manage owned studies."}
                        </p>
                      </div>
                      <span
                        className={`cdl-set-role-badge ${
                          user.role || "researcher"
                        }`}
                      >
                        {(user.role || "researcher").toUpperCase()}
                      </span>
                    </div>

                    {/* Account Actions */}
                    <div className="cdl-set-row">
                      <div className="cdl-set-row-info">
                        <span className="cdl-set-name">Account &amp; Security Profile</span>
                        <p className="cdl-set-desc">
                          Update full name, change credentials, and review activity history.
                        </p>
                      </div>
                      <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                        <Link to="/profile" className="cdl-set-btn cdl-set-btn-secondary">
                          <span>👤</span>
                          <span>Edit Profile</span>
                        </Link>
                        {isAdmin && (
                          <Link to="/admin/users" className="cdl-set-btn cdl-set-btn-primary">
                            <span>🛡️</span>
                            <span>Manage Users</span>
                          </Link>
                        )}
                      </div>
                    </div>
                  </>
                ) : (
                  <div className="cdl-set-row">
                    <div className="cdl-set-row-info">
                      <span className="cdl-set-name">No Active Session</span>
                      <p className="cdl-set-desc">
                        Authenticate with your workspace credentials to associate analyses,
                        studies, and annotations with your researcher identity.
                      </p>
                    </div>
                    <Link to="/login" className="cdl-set-btn cdl-set-btn-primary">
                      <span>🔐</span>
                      <span>Log In</span>
                    </Link>
                  </div>
                )}

                {/* Development Account Seeder */}
                <div className="cdl-set-seed-box">
                  <div style={{ display: "flex", flexDirection: "column", gap: "4px", flex: 1, minWidth: "220px" }}>
                    <span style={{ fontSize: "13px", fontWeight: "700", color: "#0f172a" }}>
                      🧪 Development Demo Accounts Seeder
                    </span>
                    <p style={{ margin: 0, fontSize: "12px", color: "#64748b" }}>
                      Initializes test research identities: <code>demo@cardiaclab.local</code> (researcher),{" "}
                      <code>reviewer@cardiaclab.local</code> (reviewer), and{" "}
                      <code>admin@cardiaclab.local</code> (administrator).
                    </p>
                    {seedMsg && (
                      <p
                        style={{
                          margin: "6px 0 0 0",
                          fontSize: "12px",
                          fontWeight: "600",
                          color: seedMsg.type === "success" ? "#16a34a" : "#dc2626",
                        }}
                      >
                        {seedMsg.type === "success" ? "✅" : "❌"} {seedMsg.text}
                      </p>
                    )}
                  </div>
                  <button
                    type="button"
                    className="cdl-set-btn cdl-set-btn-secondary"
                    onClick={handleDevSeed}
                    disabled={seeding}
                  >
                    <span>🌱</span>
                    <span>{seeding ? "Seeding Accounts..." : "Seed Dev Accounts"}</span>
                  </button>
                </div>
              </div>
            </section>
          )}

          {/* Card 2: Appearance & Theme Settings */}
          {(activeCategory === "all" || activeCategory === "appearance") && (
            <section className="cdl-set-card theme-card" aria-labelledby="card-theme-title">
              <div className="cdl-set-card-header">
                <h2 id="card-theme-title" className="cdl-set-card-title">
                  <span>🎨</span>
                  <span>Appearance &amp; Visual Environment</span>
                </h2>
                <span className="cdl-set-badge cdl-set-badge-purple">
                  Active: {theme.toUpperCase()}
                </span>
              </div>

              <div className="cdl-set-card-body">
                <div className="cdl-set-row">
                  <div className="cdl-set-row-info">
                    <span className="cdl-set-name">Interface Theme Selection</span>
                    <p className="cdl-set-desc">
                      Choose between bright daytime clinical lab viewing and dark high-contrast
                      spectrogram display for prolonged analytical sessions.
                    </p>
                  </div>
                  <button
                    type="button"
                    className="cdl-set-btn cdl-set-btn-secondary"
                    onClick={toggleTheme}
                  >
                    {theme === "light" ? "🌙 Switch to Dark Mode" : "☀️ Switch to Light Mode"}
                  </button>
                </div>

                {/* Interactive Theme Cards */}
                <div className="cdl-set-theme-picker">
                  {/* Light Mode Option */}
                  <div
                    className={`cdl-set-theme-option ${theme === "light" ? "is-active" : ""}`}
                    onClick={() => setTheme("light")}
                    role="button"
                    tabIndex={0}
                  >
                    <div className="cdl-set-theme-preview light">☀️</div>
                    <div className="cdl-set-theme-meta">
                      <span className="cdl-set-theme-name">Light Laboratory</span>
                      <span className="cdl-set-theme-sub">
                        Crisp blue-gray background with high contrast paper view
                      </span>
                    </div>
                  </div>

                  {/* Dark Mode Option */}
                  <div
                    className={`cdl-set-theme-option ${theme === "dark" ? "is-active" : ""}`}
                    onClick={() => setTheme("dark")}
                    role="button"
                    tabIndex={0}
                  >
                    <div className="cdl-set-theme-preview dark">🌙</div>
                    <div className="cdl-set-theme-meta">
                      <span className="cdl-set-theme-name">Dark Observation</span>
                      <span className="cdl-set-theme-sub">
                        Deep navy workspace optimized for vector heatmaps
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </section>
          )}

          {/* Card 3: Backend & API Configuration */}
          {(activeCategory === "all" || activeCategory === "api") && (
            <section className="cdl-set-card api-card" aria-labelledby="card-api-title">
              <div className="cdl-set-card-header">
                <h2 id="card-api-title" className="cdl-set-card-title">
                  <span>🔌</span>
                  <span>API &amp; Server Infrastructure</span>
                </h2>
                <span className="cdl-set-badge cdl-set-badge-cyan">
                  Operational
                </span>
              </div>

              <div className="cdl-set-card-body">
                {/* FastAPI Base URL */}
                <div className="cdl-set-row">
                  <div className="cdl-set-row-info">
                    <span className="cdl-set-name">FastAPI Base Gateway</span>
                    <p className="cdl-set-desc">
                      Root host endpoint for computational pipelines, optical flow jobs, and strain solvers.
                    </p>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                    <code className="cdl-set-code">{API_BASE_URL}</code>
                    <button
                      type="button"
                      className="cdl-set-btn cdl-set-btn-secondary"
                      onClick={() => handleCopyEndpoint(API_BASE_URL, "base")}
                      title="Copy base URL to clipboard"
                    >
                      {copiedKey === "base" ? "Copied" : "Copy"}
                    </button>
                  </div>
                </div>

                {/* Static Outputs Endpoint */}
                <div className="cdl-set-row">
                  <div className="cdl-set-row-info">
                    <span className="cdl-set-name">Static Heatmap Outputs</span>
                    <p className="cdl-set-desc">
                      Static asset router for serving rendered displacement and principal strain PNG maps.
                    </p>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                    <code className="cdl-set-code">{API_BASE_URL}/outputs</code>
                    <button
                      type="button"
                      className="cdl-set-btn cdl-set-btn-secondary"
                      onClick={() =>
                        handleCopyEndpoint(`${API_BASE_URL}/outputs`, "outputs")
                      }
                      title="Copy outputs URL"
                    >
                      {copiedKey === "outputs" ? "Copied" : "Copy"}
                    </button>
                  </div>
                </div>

                {/* Health Probe */}
                <div className="cdl-set-row">
                  <div className="cdl-set-row-info">
                    <span className="cdl-set-name">Health &amp; Liveness Probe</span>
                    <p className="cdl-set-desc">
                      FastAPI status route for monitoring server latency, environment, and engine health.
                    </p>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                    <code className="cdl-set-code">{API_BASE_URL}/health</code>
                    <a
                      href={`${API_BASE_URL}/health`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="cdl-set-btn cdl-set-btn-secondary"
                    >
                      ↗ Ping
                    </a>
                  </div>
                </div>

                {/* Auth Endpoint */}
                <div className="cdl-set-row">
                  <div className="cdl-set-row-info">
                    <span className="cdl-set-name">Authentication &amp; RBAC Endpoint</span>
                    <p className="cdl-set-desc">
                      Bearer JWT authorization and identity provider service router.
                    </p>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                    <code className="cdl-set-code">{API_BASE_URL}/api/auth</code>
                    <button
                      type="button"
                      className="cdl-set-btn cdl-set-btn-secondary"
                      onClick={() =>
                        handleCopyEndpoint(`${API_BASE_URL}/api/auth`, "auth")
                      }
                    >
                      {copiedKey === "auth" ? "Copied" : "Copy"}
                    </button>
                  </div>
                </div>
              </div>
            </section>
          )}

          {/* Card 4: Session & Data Cache */}
          {(activeCategory === "all" || activeCategory === "cache") && (
            <section className="cdl-set-card cache-card" aria-labelledby="card-cache-title">
              <div className="cdl-set-card-header">
                <h2 id="card-cache-title" className="cdl-set-card-title">
                  <span>💾</span>
                  <span>Session Telemetry &amp; In-Memory Cache</span>
                </h2>
                <span
                  className={`cdl-set-badge ${
                    hasCachedData ? "cdl-set-badge-cyan" : "cdl-set-badge-primary"
                  }`}
                >
                  {hasCachedData ? "Cached Data Active" : "Cache Clean"}
                </span>
              </div>

              <div className="cdl-set-card-body">
                <div className="cdl-set-row">
                  <div className="cdl-set-row-info">
                    <span className="cdl-set-name">Flush In-Memory Analysis Cache</span>
                    <p className="cdl-set-desc">
                      Clears active single-pair displacement matrices, temporal tracking arrays,
                      and rendered vector heatmaps from the current browser session. Stored study
                      history and saved JSON analyses remain safely preserved in the database.
                    </p>
                    {cacheClearedMsg && (
                      <span
                        style={{
                          fontSize: "12px",
                          color: "#16a34a",
                          fontWeight: "600",
                          marginTop: "4px",
                        }}
                      >
                        ✅ In-memory analysis cache cleared successfully.
                      </span>
                    )}
                  </div>
                  <button
                    type="button"
                    className="cdl-set-btn cdl-set-btn-danger"
                    onClick={handleClearCache}
                  >
                    <span>🗑️</span>
                    <span>Clear In-Memory Cache</span>
                  </button>
                </div>

                <div className="cdl-set-row">
                  <div className="cdl-set-row-info">
                    <span className="cdl-set-name">Active Session Status</span>
                    <p className="cdl-set-desc">Current in-memory telemetry buffers</p>
                  </div>
                  <div style={{ display: "flex", gap: "8px" }}>
                    <span className="cdl-set-badge-val">
                      Single Analysis: {latestAnalysisResult ? "Loaded" : "Empty"}
                    </span>
                    <span className="cdl-set-badge-val">
                      Temporal: {latestTemporalResult ? "Loaded" : "Empty"}
                    </span>
                  </div>
                </div>
              </div>
            </section>
          )}

          {/* Card 5: About & Research Prototype Notice */}
          {(activeCategory === "all" || activeCategory === "about") && (
            <section className="cdl-set-card about-card" aria-labelledby="card-about-title">
              <div className="cdl-set-card-header">
                <h2 id="card-about-title" className="cdl-set-card-title">
                  <span>ℹ️</span>
                  <span>System Architecture &amp; Research Prototype Notice</span>
                </h2>
                <span className="cdl-set-badge cdl-set-badge-primary">
                  Version 1.0.4
                </span>
              </div>

              <div className="cdl-set-card-body">
                <p style={{ margin: 0, fontSize: "13px", color: "#334155", lineHeight: 1.6 }}>
                  <strong>Cardiac Deformation Lab</strong> is a scientific computational research
                  platform designed for myocardial wall motion estimation, Farnebäck optical flow
                  kinematics, Green-Lagrange finite strain decomposition, and multi-session longitudinal tracking.
                </p>

                {/* Mandatory Non-Clinical Notice */}
                <div className="cdl-set-warning-box">
                  <strong>Non-Clinical Research Prototype Disclaimer:</strong>
                  <p style={{ margin: "4px 0 0 0" }}>
                    All deformation metrics, displacement vector magnitudes, principal strain eigenvalues,
                    and Temporal Stability Indices (TSI) are computed using image-space approximations.
                    This application is developed strictly for biomechanical engineering research, algorithm
                    benchmarking, and computational validation. It is <strong>NOT</strong> cleared, approved,
                    or validated for clinical diagnostic use or therapeutic patient management.
                  </p>
                </div>

                {/* Tech Stack Tags */}
                <div>
                  <span style={{ fontSize: "11px", fontWeight: "700", textTransform: "uppercase", color: "#64748b" }}>
                    Platform Architecture Specifications:
                  </span>
                  <div className="cdl-set-arch-tags">
                    <span className="cdl-set-arch-tag">FastAPI Async Core</span>
                    <span className="cdl-set-arch-tag">OpenCV Farnebäck Kinematics</span>
                    <span className="cdl-set-arch-tag">Green-Lagrange Finite Strain</span>
                    <span className="cdl-set-arch-tag">ReportLab PDF Engine</span>
                    <span className="cdl-set-arch-tag">React 19 + Vite</span>
                    <span className="cdl-set-arch-tag">PBKDF2-HMAC-SHA256 Security</span>
                    <span className="cdl-set-arch-tag">JWT Cryptographic RBAC</span>
                  </div>
                </div>
              </div>
            </section>
          )}
        </main>
      </div>
    </div>
  );
}
