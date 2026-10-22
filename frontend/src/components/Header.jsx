import { useState, useEffect, useRef } from "react";
import { useLocation, useNavigate, Link } from "react-router-dom";
import { checkBackendHealth } from "../services/api";
import { useAnalysis } from "../context/AnalysisContext";
import { useAuth } from "../context/AuthContext";
import "./Navigation.css";

const PAGE_TITLES = {
  "/": "Dashboard",
  "/studies": "Studies",
  "/analysis": "Single Pair Analysis",
  "/temporal": "Temporal Analysis",
  "/results": "Analysis Results",
  "/explorer": "Analysis Explorer",
  "/comparison": "Analysis Comparison",
  "/longitudinal": "Longitudinal Study Analysis",
  "/statistics": "Statistical Analysis",
  "/synthetic-validation": "Synthetic Validation",
  "/annotations": "Annotation Workbench",
  "/reports": "Research Reports",
  "/admin/users": "User Administration",
  "/settings": "Settings",
  "/profile": "User Profile & Security",
};

export default function Header({ onToggleSidebar }) {
  const location = useLocation();
  const navigate = useNavigate();
  const { theme, toggleTheme } = useAnalysis();
  const { user, isAuthenticated, logout, isAdmin } = useAuth();

  const [isBackendHealthy, setIsBackendHealthy] = useState(null);
  const [checking, setChecking] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const menuRef = useRef(null);

  const checkHealth = async () => {
    setChecking(true);
    const healthy = await checkBackendHealth();
    setIsBackendHealthy(healthy);
    setChecking(false);
  };

  useEffect(() => {
    checkHealth();
  }, []);

  // Close dropdown on click outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleLogout = async () => {
    setMenuOpen(false);
    await logout();
    navigate("/login");
  };

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      navigate(`/studies?search=${encodeURIComponent(searchQuery.trim())}`);
    }
  };

  let currentTitle = PAGE_TITLES[location.pathname];
  if (!currentTitle) {
    if (location.pathname.startsWith("/studies/")) {
      currentTitle = "Study Details";
    } else if (location.pathname.startsWith("/longitudinal/")) {
      currentTitle = "Longitudinal Study Analysis";
    } else if (location.pathname.startsWith("/statistics/")) {
      currentTitle = "Statistical Analysis";
    } else if (location.pathname.startsWith("/annotations/")) {
      currentTitle = "Annotation Workbench";
    } else {
      currentTitle = "Cardiac Deformation Lab";
    }
  }

  return (
    <header className="dashboard-header">
      <div className="header-left">
        <button
          className="mobile-sidebar-toggle"
          onClick={onToggleSidebar}
          aria-label="Toggle Navigation"
        >
          <span className="hamburger-bar" />
          <span className="hamburger-bar" />
          <span className="hamburger-bar" />
        </button>

        {/* Global Quick Search matching workstation screenshot reference */}
        <form className="header-search-wrap" onSubmit={handleSearchSubmit}>
          <span className="header-search-icon">🔍</span>
          <input
            type="text"
            className="header-search-input"
            placeholder="Search studies, analyses, patients, or keywords..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            aria-label="Universal Search"
          />
        </form>

        <div className="header-titles">
          <span className="header-project-name">Cardiac Deformation Lab</span>
          <span className="header-separator">/</span>
          <h2 className="header-page-title">{currentTitle}</h2>
        </div>
      </div>

      <div className="header-right">
        {/* Backend Status Indicator */}
        <div
          className={`backend-status-pill ${
            isBackendHealthy === null
              ? "status-pending"
              : isBackendHealthy
              ? "status-online"
              : "status-offline"
          }`}
          onClick={checkHealth}
          title="Click to re-check backend health"
        >
          <span className="status-dot" />
          <span className="status-text">
            {checking
              ? "Checking..."
              : isBackendHealthy === null
              ? "Checking API..."
              : isBackendHealthy
              ? "Backend Online"
              : "Backend Offline"}
          </span>
        </div>

        {/* Notification Bell with Badge */}
        <button
          type="button"
          className="header-action-btn"
          title="3 active system notifications"
          onClick={() => {}}
          aria-label="Notifications"
        >
          <span>🔔</span>
          <span className="notification-badge">3</span>
        </button>

        {/* Quick Help / Documentation Icon */}
        <button
          type="button"
          className="header-action-btn"
          title="CDL Knowledge Base & User Guide"
          onClick={() => window.open("/reports", "_self")}
          aria-label="Help Documentation"
        >
          <span>❓</span>
        </button>

        {/* Theme Toggle Button */}
        <button
          type="button"
          className="header-action-btn theme-toggle-btn"
          onClick={toggleTheme}
          title={`Switch to ${theme === "light" ? "dark" : "light"} mode`}
          aria-label="Toggle Dark Mode"
        >
          <span>{theme === "light" ? "🌙" : "☀️"}</span>
        </button>

        {/* User Workspace Menu */}
        {isAuthenticated && user && (
          <div className="user-menu-container" ref={menuRef}>
            <button
              type="button"
              className={`user-profile-btn ${menuOpen ? "is-active" : ""}`}
              onClick={() => setMenuOpen(!menuOpen)}
              aria-expanded={menuOpen}
              title="Workspace user menu"
            >
              <div className="user-avatar-circle">
                {user.name ? user.name.charAt(0).toUpperCase() : "U"}
              </div>
              <div className="user-info-text">
                <span className="user-name-display">{user.name || user.email}</span>
                <span className="user-role-display">
                  {user.role ? user.role.toUpperCase() : "RESEARCHER"}
                </span>
              </div>
              <span className={`user-menu-caret ${menuOpen ? "open" : ""}`}>▾</span>
            </button>

            {menuOpen && (
              <div className="user-dropdown-menu">
                <div className="user-dropdown-header">
                  <div className="dropdown-user-name">{user.name || "Lab Researcher"}</div>
                  <div className="dropdown-user-email">{user.email}</div>
                  <div className="dropdown-user-role-badge">
                    Role: <strong style={{ textTransform: "capitalize" }}>{user.role || "researcher"}</strong>
                  </div>
                </div>

                <div className="user-dropdown-divider" />

                <Link
                  to="/profile"
                  className="user-dropdown-item"
                  onClick={() => setMenuOpen(false)}
                >
                  <span className="dropdown-item-icon">👤</span> Profile &amp; Security
                </Link>

                <Link
                  to="/settings"
                  className="user-dropdown-item"
                  onClick={() => setMenuOpen(false)}
                >
                  <span className="dropdown-item-icon">⚙️</span> Workspace Settings
                </Link>

                {(isAdmin || user?.role === "admin") && (
                  <Link
                    to="/admin/users"
                    className="user-dropdown-item"
                    onClick={() => setMenuOpen(false)}
                  >
                    <span className="dropdown-item-icon">🛡️</span> User Administration
                  </Link>
                )}

                <div className="user-dropdown-divider" />

                <button
                  type="button"
                  className="user-dropdown-item item-logout"
                  onClick={handleLogout}
                >
                  <span className="dropdown-item-icon">🚪</span> Sign Out
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </header>
  );
}

