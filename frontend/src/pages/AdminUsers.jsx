import { useState, useEffect, useMemo, useCallback } from "react";
import { Link } from "react-router-dom";
import { getAllUsers, updateUserRole, updateUserStatus } from "../services/api";
import { useAuth } from "../context/AuthContext";
import "./AdminUsers.css";

function getInitials(name) {
  if (!name) return "U";
  const parts = name.trim().split(/\s+/);
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

function formatDate(isoStr) {
  if (!isoStr) return "N/A";
  try {
    const d = new Date(isoStr);
    return d.toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return String(isoStr);
  }
}

export default function AdminUsers() {
  const { user: currentUser } = useAuth();

  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);
  const [updatingId, setUpdatingId] = useState(null);

  // Filters & selection
  const [searchQuery, setSearchQuery] = useState("");
  const [roleFilter, setRoleFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [selectedUserId, setSelectedUserId] = useState(null);

  // Confirmation modal state for destructive action (deactivate)
  const [confirmModal, setConfirmModal] = useState({
    isOpen: false,
    user: null,
  });

  // Clipboard copy state
  const [copiedId, setCopiedId] = useState(null);

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getAllUsers();
      setUsers(data?.users || []);
    } catch (err) {
      setError(err.message || "Failed to load user list.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  // Derived selected user
  const selectedUser = useMemo(() => {
    if (!selectedUserId) return null;
    return users.find((u) => u.id === selectedUserId) || null;
  }, [users, selectedUserId]);

  // Auto-dismiss success notification
  useEffect(() => {
    if (successMsg) {
      const timer = setTimeout(() => setSuccessMsg(null), 4000);
      return () => clearTimeout(timer);
    }
  }, [successMsg]);

  // Role change handler
  const handleRoleChange = async (userId, newRole) => {
    setUpdatingId(userId);
    setError(null);
    setSuccessMsg(null);
    try {
      await updateUserRole(userId, newRole);
      setSuccessMsg(`User role successfully updated to '${newRole}'.`);
      await fetchUsers();
    } catch (err) {
      setError(err.message || "Failed to update user role.");
    } finally {
      setUpdatingId(null);
    }
  };

  // Status toggle handler
  const handleStatusToggle = async (userId, currentActive) => {
    if (userId === currentUser?.id) {
      setError("You cannot deactivate your own administrative account.");
      return;
    }

    setUpdatingId(userId);
    setError(null);
    setSuccessMsg(null);
    try {
      const nextActive = !currentActive;
      await updateUserStatus(userId, nextActive);
      setSuccessMsg(
        `User account successfully ${nextActive ? "activated" : "deactivated"}.`
      );
      await fetchUsers();
    } catch (err) {
      setError(err.message || "Failed to update user status.");
    } finally {
      setUpdatingId(null);
      setConfirmModal({ isOpen: false, user: null });
    }
  };

  // Copy helper
  const handleCopy = (text, id) => {
    if (!text) return;
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  // Filtered users
  const filteredUsers = useMemo(() => {
    return users.filter((u) => {
      // Role filter
      if (roleFilter !== "all" && u.role !== roleFilter) return false;

      // Status filter
      if (statusFilter === "active" && !u.is_active) return false;
      if (statusFilter === "deactivated" && u.is_active) return false;

      // Search query
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const name = (u.name || "").toLowerCase();
        const email = (u.email || "").toLowerCase();
        const uid = (u.id || "").toLowerCase();
        return name.includes(q) || email.includes(q) || uid.includes(q);
      }

      return true;
    });
  }, [users, roleFilter, statusFilter, searchQuery]);

  // Computed summary counts (derived strictly from real backend users)
  const stats = useMemo(() => {
    const total = users.length;
    const researchers = users.filter((u) => u.role === "researcher").length;
    const reviewers = users.filter((u) => u.role === "reviewer").length;
    const admins = users.filter((u) => u.role === "admin").length;
    const active = users.filter((u) => u.is_active).length;
    const activePercent = total > 0 ? Math.round((active / total) * 100) : 0;
    return { total, researchers, reviewers, admins, active, activePercent };
  }, [users]);

  return (
    <div className="cdl-adm-page">
      {/* 1. Header & Breadcrumbs */}
      <div className="cdl-adm-header-wrap">
        <div className="cdl-adm-title-area">
          <nav className="cdl-adm-breadcrumb" aria-label="Breadcrumb">
            <Link to="/" className="bc-link">
              <span>Home</span>
            </Link>
            <span className="bc-sep">/</span>
            <span className="bc-link">Administration</span>
            <span className="bc-sep">/</span>
            <span className="bc-current">User &amp; Access Governance</span>
          </nav>

          <div className="cdl-adm-pill-row">
            <span className="cdl-adm-badge cdl-adm-badge-primary">
              Role-Based Access Control
            </span>
            <span className="cdl-adm-badge cdl-adm-badge-cyan">
              Admin Console
            </span>
            <span className="cdl-adm-badge cdl-adm-badge-emerald">
              PBKDF2-HMAC Security
            </span>
          </div>

          <h1 className="cdl-adm-title">
            <span className="icon-accent">🛡️</span>
            Research Workspace Administration
          </h1>
          <p className="cdl-adm-subtitle">
            Manage researchers, reviewers, administrators, and workspace access.
            Review account activity, assign permissions, and oversee clinical-engineering security.
          </p>
        </div>

        <div className="cdl-adm-header-actions">
          <button
            type="button"
            className="cdl-adm-btn cdl-adm-btn-secondary"
            onClick={fetchUsers}
            disabled={loading}
          >
            {loading ? "🔄 Refreshing..." : "🔄 Refresh Accounts"}
          </button>
        </div>
      </div>

      {/* Alerts */}
      {error && (
        <div className="cdl-adm-alert error" role="alert">
          <span>❌</span>
          <div>{error}</div>
        </div>
      )}

      {successMsg && (
        <div className="cdl-adm-alert success" role="status">
          <span>✅</span>
          <div>{successMsg}</div>
        </div>
      )}

      {/* 2. Top Summary Cards (Computed strictly from real data) */}
      <section className="cdl-adm-stats-grid" aria-label="User Statistics Overview">
        {/* Total Users */}
        <div className="cdl-adm-stat-card">
          <div className="cdl-adm-stat-top">
            <span className="cdl-adm-stat-label">Total Users</span>
            <span className="cdl-adm-stat-icon">👥</span>
          </div>
          <div className="cdl-adm-stat-val">
            {loading ? "..." : stats.total}
          </div>
          <div className="cdl-adm-stat-sub">
            <span>Enrolled in workspace</span>
          </div>
        </div>

        {/* Researchers */}
        <div className="cdl-adm-stat-card researchers">
          <div className="cdl-adm-stat-top">
            <span className="cdl-adm-stat-label">Researchers</span>
            <span className="cdl-adm-stat-icon" style={{ color: "#0ea5e9" }}>
              🔬
            </span>
          </div>
          <div className="cdl-adm-stat-val">
            {loading ? "..." : stats.researchers}
          </div>
          <div className="cdl-adm-stat-sub">
            <span>Study &amp; Analysis Authors</span>
          </div>
        </div>

        {/* Reviewers */}
        <div className="cdl-adm-stat-card reviewers">
          <div className="cdl-adm-stat-top">
            <span className="cdl-adm-stat-label">Reviewers</span>
            <span className="cdl-adm-stat-icon" style={{ color: "#8b5cf6" }}>
              🔍
            </span>
          </div>
          <div className="cdl-adm-stat-val">
            {loading ? "..." : stats.reviewers}
          </div>
          <div className="cdl-adm-stat-sub">
            <span>Inspection &amp; Validation</span>
          </div>
        </div>

        {/* Administrators */}
        <div className="cdl-adm-stat-card admins">
          <div className="cdl-adm-stat-top">
            <span className="cdl-adm-stat-label">Administrators</span>
            <span className="cdl-adm-stat-icon" style={{ color: "#2563eb" }}>
              🛡️
            </span>
          </div>
          <div className="cdl-adm-stat-val">
            {loading ? "..." : stats.admins}
          </div>
          <div className="cdl-adm-stat-sub">
            <span>Workspace Governance</span>
          </div>
        </div>

        {/* Active Accounts */}
        <div className="cdl-adm-stat-card active">
          <div className="cdl-adm-stat-top">
            <span className="cdl-adm-stat-label">Active Users</span>
            <span className="cdl-adm-stat-icon" style={{ color: "#10b981" }}>
              🟢
            </span>
          </div>
          <div className="cdl-adm-stat-val">
            {loading ? "..." : stats.active}
          </div>
          <div className="cdl-adm-stat-sub">
            <span>{stats.activePercent}% operational status</span>
          </div>
        </div>
      </section>

      {/* 3. Role & Permission Architecture Card */}
      <section className="cdl-adm-rbac-card">
        <div className="cdl-adm-rbac-head">
          <div className="cdl-adm-rbac-title">
            <span>🔐</span>
            <span>Workspace Access Control &amp; Role Definitions</span>
          </div>
          <span className="cdl-adm-badge cdl-adm-badge-primary">
            Strict Multi-Tenancy
          </span>
        </div>

        <div className="cdl-adm-rbac-grid">
          {/* Researcher Role */}
          <div className="cdl-adm-role-box researcher">
            <div className="cdl-adm-role-name">
              <span>🔬</span>
              <span>Researcher</span>
            </div>
            <div className="cdl-adm-role-desc">
              Primary scientific research access. Can create and execute single-frame and
              multi-frame temporal deformation analyses, manage study cohorts, track ROIs,
              and export scientific reports.
            </div>
          </div>

          {/* Reviewer Role */}
          <div className="cdl-adm-role-box reviewer">
            <div className="cdl-adm-role-name">
              <span>🔍</span>
              <span>Reviewer</span>
            </div>
            <div className="cdl-adm-role-desc">
              Validation and inspection access. Read-only review of analysis kinematics,
              strain tensor fields, synthetic validation sweeps, and publication reports.
              Cannot create or delete studies.
            </div>
          </div>

          {/* Administrator Role */}
          <div className="cdl-adm-role-box admin">
            <div className="cdl-adm-role-name">
              <span>🛡️</span>
              <span>Administrator</span>
            </div>
            <div className="cdl-adm-role-desc">
              Full workspace administration access. Manage researcher accounts, assign RBAC roles,
              activate or deactivate logins, and inspect workspace security policies.
            </div>
          </div>
        </div>

        <div className="cdl-adm-security-notice">
          <span>🔒</span>
          <span>
            <strong>Security &amp; Access Control Policy:</strong> Passwords are never exposed or
            readable by administrators. All credentials are encrypted via PBKDF2-HMAC-SHA256 with
            100,000 iterations and cryptographically validated JWT session tokens.
          </span>
        </div>
      </section>

      {/* 4. User Management Toolbar */}
      <div className="cdl-adm-toolbar">
        <div className="cdl-adm-toolbar-left">
          {/* Search Input */}
          <div className="cdl-adm-search-input-wrap">
            <span>🔍</span>
            <input
              type="text"
              className="cdl-adm-search-input"
              placeholder="Search users by name, email, or ID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => setSearchQuery("")}
                style={{
                  background: "none",
                  border: "none",
                  cursor: "pointer",
                  color: "#94a3b8",
                  fontSize: "12px",
                }}
              >
                ✕
              </button>
            )}
          </div>

          {/* Role Filter */}
          <select
            className="cdl-adm-filter-select"
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value)}
          >
            <option value="all">All Roles</option>
            <option value="researcher">Researchers Only</option>
            <option value="reviewer">Reviewers Only</option>
            <option value="admin">Administrators Only</option>
          </select>

          {/* Status Filter */}
          <select
            className="cdl-adm-filter-select"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="all">All Statuses</option>
            <option value="active">Active Only</option>
            <option value="deactivated">Deactivated Only</option>
          </select>

          {/* Reset Filters */}
          {(roleFilter !== "all" || statusFilter !== "all" || searchQuery) && (
            <button
              type="button"
              className="cdl-adm-btn cdl-adm-btn-secondary"
              style={{ padding: "6px 12px", fontSize: "12px" }}
              onClick={() => {
                setRoleFilter("all");
                setStatusFilter("all");
                setSearchQuery("");
              }}
            >
              Reset Filters
            </button>
          )}
        </div>

        <div className="cdl-adm-toolbar-right">
          <span className="cdl-adm-user-count">
            Showing <strong>{filteredUsers.length}</strong> of {users.length} accounts
          </span>
        </div>
      </div>

      {/* 5. User Table */}
      <div className="cdl-adm-table-card">
        {loading ? (
          <div style={{ padding: "24px", display: "flex", flexDirection: "column", gap: "12px" }}>
            {[1, 2, 3, 4, 5].map((i) => (
              <div
                key={i}
                className="cdl-adm-skeleton"
                style={{ height: "48px", width: "100%" }}
              />
            ))}
          </div>
        ) : filteredUsers.length === 0 ? (
          <div className="cdl-adm-empty">
            <span className="cdl-adm-empty-icon">👥</span>
            <h3 style={{ margin: "0", color: "#0f172a" }}>No Users Found</h3>
            <p style={{ margin: "0", fontSize: "13px" }}>
              {users.length === 0
                ? "No user accounts have been registered in this workspace."
                : "No users matched your search and filter criteria."}
            </p>
          </div>
        ) : (
          <div className="cdl-adm-table-wrap">
            <table className="cdl-adm-table">
              <thead>
                <tr>
                  <th>Researcher / User</th>
                  <th>Email Address</th>
                  <th>Assigned Role</th>
                  <th>Account Status</th>
                  <th>Registration Date</th>
                  <th style={{ textAlign: "right" }}>Governance Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredUsers.map((u) => {
                  const isSelf = u.id === currentUser?.id;
                  const isBusy = updatingId === u.id;
                  const isSelected = selectedUser?.id === u.id;

                  return (
                    <tr
                      key={u.id}
                      className={isSelected ? "is-selected" : ""}
                      onClick={() => setSelectedUserId(u.id)}
                      style={{ cursor: "pointer" }}
                    >
                      {/* Name / Avatar */}
                      <td>
                        <div className="cdl-adm-user-cell">
                          <div className={`cdl-adm-avatar ${u.role}`}>
                            {getInitials(u.name)}
                          </div>
                          <div className="cdl-adm-user-info">
                            <span className="cdl-adm-user-name">
                              {u.name}
                              {isSelf && (
                                <span className="cdl-adm-self-tag">You</span>
                              )}
                            </span>
                            <span className="cdl-adm-user-id">{u.id}</span>
                          </div>
                        </div>
                      </td>

                      {/* Email */}
                      <td>
                        <span className="cdl-adm-email-cell">{u.email}</span>
                      </td>

                      {/* Role Selector */}
                      <td onClick={(e) => e.stopPropagation()}>
                        <select
                          className={`cdl-adm-role-select role-${u.role}`}
                          value={u.role}
                          onChange={(e) => handleRoleChange(u.id, e.target.value)}
                          disabled={isBusy}
                          title="Change user workspace role"
                        >
                          <option value="researcher">🔬 Researcher</option>
                          <option value="reviewer">🔍 Reviewer</option>
                          <option value="admin">🛡️ Administrator</option>
                        </select>
                      </td>

                      {/* Status */}
                      <td>
                        <span
                          className={`cdl-adm-status-badge ${
                            u.is_active ? "active" : "deactivated"
                          }`}
                        >
                          <span className="cdl-adm-status-dot" />
                          {u.is_active ? "Active" : "Deactivated"}
                        </span>
                      </td>

                      {/* Created Date */}
                      <td className="cdl-adm-date-cell">
                        {formatDate(u.created_at)}
                      </td>

                      {/* Actions */}
                      <td onClick={(e) => e.stopPropagation()}>
                        <div
                          className="cdl-adm-row-actions"
                          style={{ justifyContent: "flex-end" }}
                        >
                          <button
                            type="button"
                            className="cdl-adm-table-btn inspect"
                            onClick={() => setSelectedUserId(u.id)}
                            title="Inspect user details"
                          >
                            👁️ Details
                          </button>

                          {u.is_active ? (
                            <button
                              type="button"
                              className="cdl-adm-table-btn deactivate"
                              onClick={() => {
                                if (isSelf) {
                                  setError(
                                    "You cannot deactivate your own administrative account."
                                  );
                                  return;
                                }
                                setConfirmModal({
                                  isOpen: true,
                                  user: u,
                                });
                              }}
                              disabled={isSelf || isBusy}
                              title={
                                isSelf
                                  ? "Cannot deactivate your own session"
                                  : "Deactivate user account"
                              }
                            >
                              {isBusy ? "..." : "Deactivate"}
                            </button>
                          ) : (
                            <button
                              type="button"
                              className="cdl-adm-table-btn activate"
                              onClick={() => handleStatusToggle(u.id, u.is_active)}
                              disabled={isBusy}
                              title="Re-activate user account"
                            >
                              {isBusy ? "..." : "Activate"}
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* 6. User Details / Inspector Side Drawer */}
      {selectedUser && (
        <div
          className="cdl-adm-drawer-backdrop"
          onClick={() => setSelectedUserId(null)}
        >
          <div
            className="cdl-adm-drawer"
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-label="User Account Inspector"
          >
            {/* Drawer Header */}
            <div className="cdl-adm-drawer-header">
              <h2 className="cdl-adm-drawer-title">
                <span>🛡️</span>
                <span>User Account Inspector</span>
              </h2>
              <button
                type="button"
                className="cdl-adm-drawer-close"
                onClick={() => setSelectedUserId(null)}
                aria-label="Close inspector"
              >
                ✕
              </button>
            </div>

            {/* Drawer Body */}
            <div className="cdl-adm-drawer-body">
              {/* Profile Card */}
              <div className="cdl-adm-drawer-profile-card">
                <div className={`cdl-adm-drawer-avatar ${selectedUser.role}`}>
                  {getInitials(selectedUser.name)}
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: "3px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <strong style={{ fontSize: "16px", color: "#0f172a" }}>
                      {selectedUser.name}
                    </strong>
                    {selectedUser.id === currentUser?.id && (
                      <span className="cdl-adm-self-tag">Your Account</span>
                    )}
                  </div>
                  <span
                    style={{
                      fontSize: "13px",
                      color: "#64748b",
                      fontFamily: "ui-monospace, monospace",
                    }}
                  >
                    {selectedUser.email}
                  </span>
                  <div style={{ marginTop: "4px" }}>
                    <span
                      className={`cdl-adm-status-badge ${
                        selectedUser.is_active ? "active" : "deactivated"
                      }`}
                    >
                      <span className="cdl-adm-status-dot" />
                      {selectedUser.is_active ? "Active" : "Deactivated"}
                    </span>
                  </div>
                </div>
              </div>

              {/* Role Management */}
              <div className="cdl-adm-drawer-meta-section">
                <h3 className="cdl-adm-drawer-meta-title">
                  Assigned Workspace Role
                </h3>
                <div
                  style={{
                    background: "#f8fafc",
                    border: "1px solid #e2e8f0",
                    borderRadius: "8px",
                    padding: "14px",
                    display: "flex",
                    flexDirection: "column",
                    gap: "10px",
                  }}
                >
                  <select
                    className={`cdl-adm-role-select role-${selectedUser.role}`}
                    value={selectedUser.role}
                    onChange={(e) =>
                      handleRoleChange(selectedUser.id, e.target.value)
                    }
                    disabled={updatingId === selectedUser.id}
                    style={{ width: "100%", padding: "8px 12px", fontSize: "13px" }}
                  >
                    <option value="researcher">🔬 Researcher (Full Analysis Access)</option>
                    <option value="reviewer">🔍 Reviewer (Read-Only Inspection)</option>
                    <option value="admin">🛡️ Administrator (Governance &amp; RBAC)</option>
                  </select>
                  <p style={{ margin: 0, fontSize: "12px", color: "#64748b", lineHeight: 1.4 }}>
                    {selectedUser.role === "researcher" &&
                      "Researchers can upload image sequences, execute Farnebäck optical flow analyses, track ROIs, and create studies."}
                    {selectedUser.role === "reviewer" &&
                      "Reviewers have inspection permissions across analysis reports and validation charts. They cannot initiate or modify analyses."}
                    {selectedUser.role === "admin" &&
                      "Administrators have full access to workspace user accounts, authorization roles, and system configuration."}
                  </p>
                </div>
              </div>

              {/* Account Metadata Grid */}
              <div className="cdl-adm-drawer-meta-section">
                <h3 className="cdl-adm-drawer-meta-title">
                  Security &amp; Account Metadata
                </h3>
                <div className="cdl-adm-drawer-meta-grid">
                  <div className="cdl-adm-drawer-meta-row">
                    <span className="label">User Identifier:</span>
                    <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                      <span className="value">
                        {selectedUser.id ? `${selectedUser.id.slice(0, 12)}...` : "N/A"}
                      </span>
                      <button
                        type="button"
                        onClick={() => handleCopy(selectedUser.id, "drawer-id")}
                        style={{
                          background: "none",
                          border: "none",
                          cursor: "pointer",
                          color: "#3b82f6",
                          fontSize: "11px",
                        }}
                      >
                        {copiedId === "drawer-id" ? "Copied" : "Copy"}
                      </button>
                    </div>
                  </div>

                  <div className="cdl-adm-drawer-meta-row">
                    <span className="label">Registered At:</span>
                    <span className="value">{formatDate(selectedUser.created_at)}</span>
                  </div>

                  <div className="cdl-adm-drawer-meta-row">
                    <span className="label">Profile Updated:</span>
                    <span className="value">{formatDate(selectedUser.updated_at)}</span>
                  </div>

                  <div className="cdl-adm-drawer-meta-row">
                    <span className="label">Authentication:</span>
                    <span className="value">PBKDF2-HMAC-SHA256</span>
                  </div>

                  <div className="cdl-adm-drawer-meta-row">
                    <span className="label">Session Auth:</span>
                    <span className="value">Cryptographic JWT</span>
                  </div>
                </div>
              </div>

              {/* Account Status Governance */}
              <div className="cdl-adm-drawer-meta-section">
                <h3 className="cdl-adm-drawer-meta-title">Account Governance</h3>
                <div
                  style={{
                    background: "#f8fafc",
                    border: "1px solid #e2e8f0",
                    borderRadius: "8px",
                    padding: "14px",
                    display: "flex",
                    flexDirection: "column",
                    gap: "10px",
                  }}
                >
                  <p style={{ margin: 0, fontSize: "12px", color: "#64748b" }}>
                    Deactivating an account temporarily suspends all workspace login privileges
                    and prevents running computational analyses without deleting existing studies.
                  </p>
                  {selectedUser.id === currentUser?.id ? (
                    <div
                      style={{
                        fontSize: "12px",
                        color: "#92400e",
                        background: "#fef3c7",
                        padding: "8px 12px",
                        borderRadius: "6px",
                      }}
                    >
                      ⚠️ You are logged in as this user and cannot deactivate your own account.
                    </div>
                  ) : selectedUser.is_active ? (
                    <button
                      type="button"
                      className="cdl-adm-btn cdl-adm-btn-danger"
                      onClick={() =>
                        setConfirmModal({
                          isOpen: true,
                          user: selectedUser,
                        })
                      }
                      disabled={updatingId === selectedUser.id}
                      style={{ alignSelf: "flex-start" }}
                    >
                      {updatingId === selectedUser.id
                        ? "Deactivating..."
                        : "Deactivate User Account"}
                    </button>
                  ) : (
                    <button
                      type="button"
                      className="cdl-adm-btn cdl-adm-btn-primary"
                      onClick={() =>
                        handleStatusToggle(selectedUser.id, selectedUser.is_active)
                      }
                      disabled={updatingId === selectedUser.id}
                      style={{ alignSelf: "flex-start" }}
                    >
                      {updatingId === selectedUser.id
                        ? "Activating..."
                        : "Re-activate User Account"}
                    </button>
                  )}
                </div>
              </div>
            </div>

            {/* Drawer Footer */}
            <div className="cdl-adm-drawer-footer">
              <button
                type="button"
                className="cdl-adm-btn cdl-adm-btn-secondary"
                onClick={() => setSelectedUserId(null)}
              >
                Close Inspector
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 7. Confirmation Modal for Deactivation */}
      {confirmModal.isOpen && confirmModal.user && (
        <div
          className="cdl-adm-modal-backdrop"
          onClick={() => setConfirmModal({ isOpen: false, user: null })}
        >
          <div
            className="cdl-adm-modal"
            onClick={(e) => e.stopPropagation()}
            role="alertdialog"
            aria-labelledby="confirm-modal-title"
          >
            <div className="cdl-adm-modal-head">
              <div className="cdl-adm-modal-icon">⚠️</div>
              <h3 id="confirm-modal-title" className="cdl-adm-modal-title">
                Confirm Account Deactivation
              </h3>
            </div>

            <p className="cdl-adm-modal-p">
              Are you sure you want to deactivate the account for{" "}
              <strong>{confirmModal.user.name}</strong> (
              <code>{confirmModal.user.email}</code>)?
            </p>
            <p className="cdl-adm-modal-p" style={{ fontSize: "12px", color: "#64748b" }}>
              This user will immediately be locked out of the Cardiac Deformation Lab
              workspace until re-activated by an administrator. Their historical studies,
              analyses, and annotations will be preserved.
            </p>

            <div className="cdl-adm-modal-actions">
              <button
                type="button"
                className="cdl-adm-btn cdl-adm-btn-secondary"
                onClick={() => setConfirmModal({ isOpen: false, user: null })}
                disabled={updatingId === confirmModal.user.id}
              >
                Cancel
              </button>
              <button
                type="button"
                className="cdl-adm-btn cdl-adm-btn-danger"
                onClick={() =>
                  handleStatusToggle(
                    confirmModal.user.id,
                    confirmModal.user.is_active
                  )
                }
                disabled={updatingId === confirmModal.user.id}
              >
                {updatingId === confirmModal.user.id
                  ? "Deactivating..."
                  : "Confirm Deactivation"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
