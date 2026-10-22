import React, { useState } from "react";
import { useAuth } from "../context/AuthContext";
import { updateUserProfile } from "../services/api";
import "./Settings.css";

export default function Profile() {
  const { user, updateProfileState } = useAuth();

  const [name, setName] = useState(user?.name || "");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmNewPassword, setConfirmNewPassword] = useState("");

  const [nameLoading, setNameLoading] = useState(false);
  const [passwordLoading, setPasswordLoading] = useState(false);
  const [nameSuccess, setNameSuccess] = useState(null);
  const [passwordSuccess, setPasswordSuccess] = useState(null);
  const [error, setError] = useState(null);

  const handleUpdateName = async (e) => {
    e.preventDefault();
    setError(null);
    setNameSuccess(null);

    if (!name.trim()) {
      setError("Name cannot be empty.");
      return;
    }

    setNameLoading(true);
    try {
      const res = await updateUserProfile({ name: name.trim() });
      if (res?.user) {
        updateProfileState(res.user);
      }
      setNameSuccess("Profile name updated successfully.");
    } catch (err) {
      setError(err.message || "Failed to update profile name.");
    } finally {
      setNameLoading(false);
    }
  };

  const handleUpdatePassword = async (e) => {
    e.preventDefault();
    setError(null);
    setPasswordSuccess(null);

    if (!currentPassword) {
      setError("Please provide your current password.");
      return;
    }

    if (newPassword.length < 8) {
      setError("New password must be at least 8 characters long.");
      return;
    }

    if (newPassword !== confirmNewPassword) {
      setError("New passwords do not match.");
      return;
    }

    setPasswordLoading(true);
    try {
      await updateUserProfile({
        current_password: currentPassword,
        new_password: newPassword
      });
      setPasswordSuccess("Password changed successfully.");
      setCurrentPassword("");
      setNewPassword("");
      setConfirmNewPassword("");
    } catch (err) {
      setError(err.message || "Failed to change password. Please check your current password.");
    } finally {
      setPasswordLoading(false);
    }
  };

  const formatDate = (isoStr) => {
    if (!isoStr) return "N/A";
    try {
      return new Date(isoStr).toLocaleDateString(undefined, {
        year: "numeric",
        month: "long",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit"
      });
    } catch (_) {
      return isoStr;
    }
  };

  return (
    <div className="cdl-set-page" style={{ maxWidth: "1280px" }}>
      {/* 1. Header & Breadcrumb */}
      <div className="cdl-set-header-wrap">
        <div>
          <div className="cdl-set-breadcrumb">
            <span className="bc-link">🔬 Research Workspace</span>
            <span className="bc-sep">/</span>
            <span className="bc-current">User Profile &amp; Security</span>
          </div>
          <h1 className="cdl-set-title">Researcher Profile &amp; Security</h1>
          <p className="cdl-set-subtitle">
            Manage your research workspace identity, assigned role permissions, and account authentication credentials.
          </p>
        </div>

        <div className="cdl-set-header-actions">
          <span className="cdl-set-chip cdl-set-chip-blue">
            Role: <strong style={{ textTransform: "capitalize", marginLeft: "4px" }}>{user?.role || "Researcher"}</strong>
          </span>
          <span className="cdl-set-chip cdl-set-chip-cyan">
            Active Session
          </span>
        </div>
      </div>

      {/* Disclaimers & Alerts */}
      {error && (
        <div className="cdl-set-alert cdl-set-alert-danger" role="alert">
          <span className="alert-icon">⚠️</span>
          <div className="alert-body">
            <strong>Action Failed:</strong> {error}
          </div>
        </div>
      )}

      {nameSuccess && (
        <div className="cdl-set-alert cdl-set-alert-success" role="status">
          <span className="alert-icon">✓</span>
          <div className="alert-body">
            <strong>Success:</strong> {nameSuccess}
          </div>
        </div>
      )}

      {passwordSuccess && (
        <div className="cdl-set-alert cdl-set-alert-success" role="status">
          <span className="alert-icon">✓</span>
          <div className="alert-body">
            <strong>Success:</strong> {passwordSuccess}
          </div>
        </div>
      )}

      {/* Main Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))", gap: "24px" }}>
        {/* Account Details Card */}
        <div className="cdl-set-card">
          <div className="cdl-set-card-header">
            <div className="card-header-icon icon-blue">👤</div>
            <div>
              <h2 className="cdl-set-card-title">Account Credentials</h2>
              <p className="cdl-set-card-subtitle">Workspace user metadata and access clearance</p>
            </div>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "14px", marginTop: "16px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", paddingBottom: "10px", borderBottom: "1px solid var(--border-color, #e2e8f0)" }}>
              <span style={{ fontSize: "12.5px", color: "var(--text-muted, #64748b)", fontWeight: "500" }}>Full Name</span>
              <strong style={{ fontSize: "13px", color: "var(--text-main, #0f172a)" }}>{user?.name || "N/A"}</strong>
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", paddingBottom: "10px", borderBottom: "1px solid var(--border-color, #e2e8f0)" }}>
              <span style={{ fontSize: "12.5px", color: "var(--text-muted, #64748b)", fontWeight: "500" }}>Email Address</span>
              <span style={{ fontSize: "13px", color: "var(--text-main, #0f172a)", fontFamily: "var(--font-mono)" }}>{user?.email || "N/A"}</span>
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", paddingBottom: "10px", borderBottom: "1px solid var(--border-color, #e2e8f0)" }}>
              <span style={{ fontSize: "12.5px", color: "var(--text-muted, #64748b)", fontWeight: "500" }}>Assigned Role</span>
              <span className={`cdl-set-chip ${user?.role === "admin" ? "cdl-set-chip-blue" : "cdl-set-chip-cyan"}`}>
                {user?.role ? user.role.toUpperCase() : "RESEARCHER"}
              </span>
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", paddingBottom: "10px", borderBottom: "1px solid var(--border-color, #e2e8f0)" }}>
              <span style={{ fontSize: "12.5px", color: "var(--text-muted, #64748b)", fontWeight: "500" }}>Account Registered</span>
              <span style={{ fontSize: "12.5px", color: "var(--text-main, #0f172a)" }}>{formatDate(user?.created_at)}</span>
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: "12.5px", color: "var(--text-muted, #64748b)", fontWeight: "500" }}>Workspace Identifier</span>
              <code style={{ fontSize: "11.5px" }}>{user?.id ? `${user.id.slice(0, 12)}...` : "N/A"}</code>
            </div>
          </div>

          <div style={{ marginTop: "20px", padding: "12px 14px", background: "rgba(245, 158, 11, 0.08)", border: "1px solid rgba(245, 158, 11, 0.25)", borderRadius: "8px" }}>
            <span style={{ fontSize: "11px", fontWeight: "700", color: "#d97706", display: "block", marginBottom: "3px" }}>
              RESEARCH ACCESS ONLY
            </span>
            <p style={{ fontSize: "11px", color: "var(--text-muted, #64748b)", margin: 0, lineHeight: 1.4 }}>
              This account authenticates access to computational biomechanics tools. It does not certify medical or diagnostic authority.
            </p>
          </div>
        </div>

        {/* Change Name Form */}
        <div className="cdl-set-card">
          <div className="cdl-set-card-header">
            <div className="card-header-icon icon-cyan">✏️</div>
            <div>
              <h2 className="cdl-set-card-title">Edit Display Name</h2>
              <p className="cdl-set-card-subtitle">Public name displayed on analyses and generated reports</p>
            </div>
          </div>

          <form onSubmit={handleUpdateName} style={{ display: "flex", flexDirection: "column", gap: "16px", marginTop: "16px" }}>
            <div className="cdl-set-form-group">
              <label htmlFor="prof-name" className="cdl-set-label">
                Display Name <span className="req">*</span>
              </label>
              <input
                id="prof-name"
                type="text"
                className="cdl-set-input"
                value={name}
                onChange={(e) => setName(e.target.value)}
                disabled={nameLoading}
                required
              />
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", marginTop: "4px" }}>
              <button
                type="submit"
                className="cdl-set-btn cdl-set-btn-primary"
                disabled={nameLoading}
              >
                {nameLoading ? "Saving..." : "Save Display Name"}
              </button>
            </div>
          </form>
        </div>

        {/* Change Password Form */}
        <div className="cdl-set-card" style={{ gridColumn: "1 / -1" }}>
          <div className="cdl-set-card-header">
            <div className="card-header-icon icon-purple">🔒</div>
            <div>
              <h2 className="cdl-set-card-title">Security &amp; Password Management</h2>
              <p className="cdl-set-card-subtitle">
                Secured via PBKDF2-HMAC-SHA256 password hashing with salt and 100,000 iterations
              </p>
            </div>
          </div>

          <form onSubmit={handleUpdatePassword} style={{ maxWidth: "620px", display: "flex", flexDirection: "column", gap: "16px", marginTop: "16px" }}>
            <div className="cdl-set-form-group">
              <label htmlFor="cur-pass" className="cdl-set-label">
                Current Password <span className="req">*</span>
              </label>
              <input
                id="cur-pass"
                type="password"
                className="cdl-set-input"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                disabled={passwordLoading}
                placeholder="••••••••••••"
                required
              />
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
              <div className="cdl-set-form-group">
                <label htmlFor="new-pass" className="cdl-set-label">
                  New Password <span className="req">*</span>
                </label>
                <input
                  id="new-pass"
                  type="password"
                  className="cdl-set-input"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  disabled={passwordLoading}
                  placeholder="Min 8 characters"
                  required
                />
              </div>

              <div className="cdl-set-form-group">
                <label htmlFor="conf-new-pass" className="cdl-set-label">
                  Confirm Password <span className="req">*</span>
                </label>
                <input
                  id="conf-new-pass"
                  type="password"
                  className="cdl-set-input"
                  value={confirmNewPassword}
                  onChange={(e) => setConfirmNewPassword(e.target.value)}
                  disabled={passwordLoading}
                  placeholder="Repeat new password"
                  required
                />
              </div>
            </div>

            <div style={{ display: "flex", justifyContent: "flex-start", marginTop: "8px" }}>
              <button
                type="submit"
                className="cdl-set-btn cdl-set-btn-primary"
                disabled={passwordLoading}
              >
                {passwordLoading ? "Updating Password..." : "Update Security Credentials"}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

