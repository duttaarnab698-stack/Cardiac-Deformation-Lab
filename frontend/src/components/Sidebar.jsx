import { useEffect, useRef } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import "./Navigation.css";

const BASE_NAV_ITEMS = [
  { path: "/", label: "Dashboard", icon: "📊" },
  { path: "/studies", label: "Studies", icon: "📁" },
  { path: "/analysis", label: "Analysis", icon: "🔬" },
  { path: "/temporal", label: "Temporal Analysis", icon: "⏱️" },
  { path: "/results", label: "Analysis Results", icon: "📈" },
  { path: "/explorer", label: "Analysis Explorer", icon: "🔭" },
  { path: "/comparison", label: "Comparison", icon: "⚖️" },
  { path: "/longitudinal", label: "Longitudinal", icon: "📉" },
  { path: "/statistics", label: "Statistics", icon: "📐" },
  { path: "/synthetic-validation", label: "Synthetic Validation", icon: "🧪" },
  { path: "/annotations", label: "Annotation", icon: "✏️" },
  { path: "/reports", label: "Research Reports", icon: "📑" },
  { path: "/settings", label: "Settings", icon: "⚙️" },
];

export default function Sidebar({ isOpen, onClose }) {
  const { user, isAdmin } = useAuth();
  const location = useLocation();
  const navContainerRef = useRef(null);

  // Ensure sidebar navigation always resets to the top (Dashboard) on route changes & mount
  useEffect(() => {
    if (navContainerRef.current) {
      navContainerRef.current.scrollTop = 0;
    }
  }, [location.pathname]);

  const navItems = [...BASE_NAV_ITEMS];
  if (isAdmin || user?.role === "admin") {
    // Exact position: Item 13 (before Settings)
    navItems.splice(navItems.length - 1, 0, {
      path: "/admin/users",
      label: "User Admin",
      icon: "👥",
    });
  }

  // Active route matching helper for nested sub-routes
  const checkIsActive = (itemPath) => {
    if (itemPath === "/") {
      return location.pathname === "/";
    }
    if (itemPath === "/studies") {
      return location.pathname === "/studies" || location.pathname.startsWith("/studies/");
    }
    if (itemPath === "/longitudinal") {
      return location.pathname === "/longitudinal" || location.pathname.startsWith("/longitudinal/");
    }
    if (itemPath === "/annotations") {
      return location.pathname === "/annotations" || location.pathname.startsWith("/annotations/");
    }
    if (itemPath === "/statistics") {
      return location.pathname === "/statistics" || location.pathname.startsWith("/statistics/");
    }
    return location.pathname === itemPath || location.pathname.startsWith(itemPath + "/");
  };

  return (
    <>
      {/* Mobile backdrop */}
      {isOpen && (
        <div
          className="sidebar-backdrop"
          onClick={onClose}
          aria-hidden="true"
        />
      )}
      <aside className={`dashboard-sidebar ${isOpen ? "open" : ""}`}>
        {/* Brand Header */}
        <div className="sidebar-brand">
          <div className="brand-logo-icon">🫀</div>
          <div className="brand-info">
            <span className="brand-title">CDL Prototype</span>
            <span className="brand-subtitle">v1.0.4 Research Lab</span>
          </div>
        </div>

        {/* User & Role Status Card */}
        {user && (
          <div className="sidebar-user-card-wrap">
            <div className="sidebar-user-card">
              <div className="user-card-status-row">
                <span className="online-indicator-dot" />
                <span className="user-card-name" title={user.name || user.email}>
                  {user.name || user.email}
                </span>
              </div>
              <div className="user-card-role-row">
                <span
                  className={`user-card-role-badge badge-${
                    user.role?.toLowerCase() || "researcher"
                  }`}
                >
                  {user.role ? user.role.toUpperCase() : "RESEARCHER"}
                </span>
                <span className="user-card-status-text">Active Lab</span>
              </div>
            </div>
          </div>
        )}

        {/* Navigation Section Title */}
        <div className="sidebar-nav-header">
          <span className="nav-section-title">NAVIGATION</span>
        </div>

        {/* Scrollable Navigation List */}
        <div className="sidebar-nav-container" ref={navContainerRef}>
          <nav className="sidebar-nav">
            {navItems.map((item) => {
              const active = checkIsActive(item.path);
              return (
                <NavLink
                  key={item.path}
                  to={item.path}
                  className={`nav-link ${active ? "active" : ""}`}
                  onClick={onClose}
                >
                  <span className="nav-icon">{item.icon}</span>
                  <span className="nav-label">{item.label}</span>
                </NavLink>
              );
            })}
          </nav>
        </div>

        {/* Pinned Bottom Disclaimer Card */}
        <div className="sidebar-footer">
          <div className="sidebar-disclaimer-card">
            <div className="disclaimer-badge-row">
              <span className="disclaimer-icon">⚠️</span>
              <span className="disclaimer-badge">RESEARCH ONLY</span>
            </div>
            <p className="disclaimer-text">
              Image-space kinematic estimation. Not for diagnostic use.
            </p>
          </div>
        </div>
      </aside>
    </>
  );
}

