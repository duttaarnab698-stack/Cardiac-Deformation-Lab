import { useState, useEffect, useMemo, useCallback } from "react";
import { Link } from "react-router-dom";
import { getStudies, createStudy, deleteStudy, updateStudy } from "../services/api";
import "./Studies.css";

function formatDate(isoString) {
  if (!isoString) return "N/A";
  try {
    const d = new Date(isoString);
    return d.toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return String(isoString).slice(0, 10);
  }
}

export default function Studies() {
  const [studies, setStudies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionMsg, setActionMsg] = useState("");

  // Search & Filter State
  const [searchQuery, setSearchQuery] = useState("");
  const [filterCohort, setFilterCohort] = useState("all"); // "all" | "active" | "empty"
  const [sortOrder, setSortOrder] = useState("newest"); // "newest" | "oldest" | "title" | "analyses"
  const [viewMode, setViewMode] = useState("table"); // "table" | "grid"
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 10;

  // Create Modal State
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [createTitle, setCreateTitle] = useState("");
  const [createSubjectCode, setCreateSubjectCode] = useState("");
  const [createDescription, setCreateDescription] = useState("");
  const [creating, setCreating] = useState(false);
  const [createModalError, setCreateModalError] = useState("");

  // Edit Modal State
  const [editingStudy, setEditingStudy] = useState(null);
  const [editTitle, setEditTitle] = useState("");
  const [editSubjectCode, setEditSubjectCode] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [savingEdit, setSavingEdit] = useState(false);
  const [editModalError, setEditModalError] = useState("");

  const fetchStudies = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getStudies();
      setStudies(data || []);
    } catch (err) {
      setError(err.message || "Failed to load research studies.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStudies();
  }, [fetchStudies]);

  // Derived KPI Metrics from real study data
  const totalStudiesCount = studies.length;
  const activeCohortsCount = useMemo(
    () => studies.filter((s) => s.analysis_ids && s.analysis_ids.length > 0).length,
    [studies]
  );
  const totalAnalysesLinked = useMemo(
    () =>
      studies.reduce(
        (acc, s) => acc + (s.analysis_ids ? s.analysis_ids.length : 0),
        0
      ),
    [studies]
  );
  const uniqueSubjectsCount = useMemo(() => {
    const set = new Set();
    studies.forEach((s) => {
      if (s.subject_code && s.subject_code.trim()) {
        set.add(s.subject_code.trim());
      }
    });
    return set.size;
  }, [studies]);

  // Filtered and Sorted Studies
  const processedStudies = useMemo(() => {
    let result = [...studies];

    // Search query filter
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter(
        (s) =>
          (s.title && s.title.toLowerCase().includes(q)) ||
          (s.subject_code && s.subject_code.toLowerCase().includes(q)) ||
          (s.id && s.id.toLowerCase().includes(q)) ||
          (s.description && s.description.toLowerCase().includes(q))
      );
    }

    // Cohort analysis filter
    if (filterCohort === "active") {
      result = result.filter((s) => s.analysis_ids && s.analysis_ids.length > 0);
    } else if (filterCohort === "empty") {
      result = result.filter((s) => !s.analysis_ids || s.analysis_ids.length === 0);
    }

    // Sorting
    result.sort((a, b) => {
      if (sortOrder === "newest") {
        return new Date(b.created_at || 0) - new Date(a.created_at || 0);
      }
      if (sortOrder === "oldest") {
        return new Date(a.created_at || 0) - new Date(b.created_at || 0);
      }
      if (sortOrder === "title") {
        return (a.title || "").localeCompare(b.title || "");
      }
      if (sortOrder === "analyses") {
        return (b.analysis_ids?.length || 0) - (a.analysis_ids?.length || 0);
      }
      return 0;
    });

    return result;
  }, [studies, searchQuery, filterCohort, sortOrder]);

  // Pagination calculation
  const totalPages = Math.ceil(processedStudies.length / itemsPerPage) || 1;
  const paginatedStudies = useMemo(() => {
    const start = (currentPage - 1) * itemsPerPage;
    return processedStudies.slice(start, start + itemsPerPage);
  }, [processedStudies, currentPage]);

  const handlePageChange = (newPage) => {
    if (newPage >= 1 && newPage <= totalPages) {
      setCurrentPage(newPage);
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  };

  // Reset pagination on search or filter change
  useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery, filterCohort, sortOrder]);

  // Create Study Handler
  const handleCreateSubmit = async (e) => {
    e.preventDefault();
    if (!createTitle.trim()) {
      setCreateModalError("Study Title is required.");
      return;
    }

    setCreating(true);
    setCreateModalError("");
    try {
      await createStudy({
        title: createTitle.trim(),
        subject_code: createSubjectCode.trim() || undefined,
        description: createDescription.trim() || undefined,
      });
      setShowCreateModal(false);
      setCreateTitle("");
      setCreateSubjectCode("");
      setCreateDescription("");
      setActionMsg("Research study created successfully.");
      await fetchStudies();
    } catch (err) {
      setCreateModalError(err.message || "Failed to create research study.");
    } finally {
      setCreating(false);
    }
  };

  // Edit Study Handlers
  const handleStartEdit = (e, study) => {
    e.preventDefault();
    e.stopPropagation();
    setEditingStudy(study);
    setEditTitle(study.title || "");
    setEditSubjectCode(study.subject_code || "");
    setEditDescription(study.description || "");
    setEditModalError("");
  };

  const handleEditSubmit = async (e) => {
    e.preventDefault();
    if (!editingStudy || !editTitle.trim()) {
      setEditModalError("Study Title is required.");
      return;
    }

    setSavingEdit(true);
    setEditModalError("");
    try {
      await updateStudy(editingStudy.id, {
        title: editTitle.trim(),
        subject_code: editSubjectCode.trim() || undefined,
        description: editDescription.trim() || undefined,
      });
      setEditingStudy(null);
      setActionMsg("Study details updated successfully.");
      await fetchStudies();
    } catch (err) {
      setEditModalError(err.message || "Failed to update study.");
    } finally {
      setSavingEdit(false);
    }
  };

  // Delete Study Handler
  const handleDelete = async (e, studyId, title) => {
    e.preventDefault();
    e.stopPropagation();

    if (
      !window.confirm(
        `Are you sure you want to delete research study "${title}"?\n\nNOTE: Associated analyses, generated reports, and uploaded files will NOT be deleted from global history.`
      )
    ) {
      return;
    }

    try {
      await deleteStudy(studyId);
      setActionMsg(`Research study "${title}" deleted.`);
      await fetchStudies();
    } catch (err) {
      setError(err.message || "Failed to delete research study.");
    }
  };

  return (
    <div className="cdl-studies-page">
      {/* 1. PAGE HEADER & BREADCRUMB */}
      <section className="cdl-studies-header-wrap" aria-label="Page Header">
        <div className="cdl-studies-header-left">
          <div className="cdl-studies-breadcrumb">
            <Link to="/" className="bc-home">
              <span>🔬</span>
              <span>Workspace</span>
            </Link>
            <span className="bc-sep">/</span>
            <span className="bc-current">Research Studies</span>
          </div>

          <h1 className="cdl-studies-title">Research Studies</h1>
          <p className="cdl-studies-subtitle">
            Organize cardiac deformation studies, analyses, cohorts, and kinematic research results.
          </p>
        </div>

        <button
          type="button"
          className="cdl-btn-primary-action"
          onClick={() => {
            setShowCreateModal(true);
            setCreateModalError("");
          }}
        >
          <span>➕</span>
          <span>New Study</span>
        </button>
      </section>

      {/* STATUS BANNERS */}
      {actionMsg && (
        <div className="cdl-alert-banner cdl-alert-success" role="status">
          <span>✓ {actionMsg}</span>
          <button
            className="cdl-btn-table-icon"
            onClick={() => setActionMsg("")}
            title="Dismiss notice"
          >
            ✕
          </button>
        </div>
      )}

      {error && (
        <div className="cdl-alert-banner cdl-alert-error" role="alert">
          <div>
            <strong>Service Notice:</strong> {error}
          </div>
          <button className="cdl-btn-table-action" onClick={fetchStudies}>
            Retry
          </button>
        </div>
      )}

      {/* 2. SUMMARY KPI ROW */}
      <section className="cdl-studies-kpi-grid" aria-label="Studies Metrics">
        {/* Metric 1: Total Studies */}
        <div className="cdl-studies-kpi-card kpi-border-blue">
          <div className="cdl-studies-kpi-header">
            <div className="cdl-studies-kpi-icon kpi-icon-blue">📁</div>
            <span className="cdl-studies-kpi-pill">STUDIES</span>
          </div>
          <div className="cdl-studies-kpi-value">
            {loading ? "..." : totalStudiesCount}
          </div>
          <div className="cdl-studies-kpi-label">Total Studies</div>
          <div className="cdl-studies-kpi-subtext">Registered cohort registries</div>
        </div>

        {/* Metric 2: Active Cohorts */}
        <div className="cdl-studies-kpi-card kpi-border-purple">
          <div className="cdl-studies-kpi-header">
            <div className="cdl-studies-kpi-icon kpi-icon-purple">📊</div>
            <span className="cdl-studies-kpi-pill">ACTIVE</span>
          </div>
          <div className="cdl-studies-kpi-value">
            {loading ? "..." : activeCohortsCount}
          </div>
          <div className="cdl-studies-kpi-label">Active Cohorts</div>
          <div className="cdl-studies-kpi-subtext">Studies with linked deformation analyses</div>
        </div>

        {/* Metric 3: Total Analyses Linked */}
        <div className="cdl-studies-kpi-card kpi-border-cyan">
          <div className="cdl-studies-kpi-header">
            <div className="cdl-studies-kpi-icon kpi-icon-cyan">🔬</div>
            <span className="cdl-studies-kpi-pill">ANALYSES</span>
          </div>
          <div className="cdl-studies-kpi-value">
            {loading ? "..." : totalAnalysesLinked}
          </div>
          <div className="cdl-studies-kpi-label">Analyses Linked</div>
          <div className="cdl-studies-kpi-subtext">Combined single-pair &amp; temporal sessions</div>
        </div>

        {/* Metric 4: Pseudonymous Subjects */}
        <div className="cdl-studies-kpi-card kpi-border-emerald">
          <div className="cdl-studies-kpi-header">
            <div className="cdl-studies-kpi-icon kpi-icon-emerald">🏷️</div>
            <span className="cdl-studies-kpi-pill">SUBJECTS</span>
          </div>
          <div className="cdl-studies-kpi-value">
            {loading ? "..." : uniqueSubjectsCount}
          </div>
          <div className="cdl-studies-kpi-label">Unique Subjects</div>
          <div className="cdl-studies-kpi-subtext">Pseudonymous research identifiers</div>
        </div>
      </section>

      {/* 3. SEARCH & FILTER TOOLBAR */}
      <section className="cdl-studies-toolbar" aria-label="Studies Filtering">
        <div className="cdl-studies-search-box">
          <span className="cdl-studies-search-icon">🔍</span>
          <input
            type="text"
            className="cdl-studies-search-input"
            placeholder="Search by study name, subject code, ID..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
          {searchQuery && (
            <button
              className="cdl-studies-search-clear"
              onClick={() => setSearchQuery("")}
              title="Clear search"
            >
              ✕
            </button>
          )}
        </div>

        <div className="cdl-studies-filter-group">
          <select
            className="cdl-studies-select"
            value={filterCohort}
            onChange={(e) => setFilterCohort(e.target.value)}
            aria-label="Filter by cohort status"
          >
            <option value="all">All Cohorts ({studies.length})</option>
            <option value="active">With Analyses ({activeCohortsCount})</option>
            <option value="empty">
              Without Analyses ({studies.length - activeCohortsCount})
            </option>
          </select>

          <select
            className="cdl-studies-select"
            value={sortOrder}
            onChange={(e) => setSortOrder(e.target.value)}
            aria-label="Sort studies"
          >
            <option value="newest">Sort: Newest First</option>
            <option value="oldest">Sort: Oldest First</option>
            <option value="title">Sort: Title (A-Z)</option>
            <option value="analyses">Sort: Most Analyses</option>
          </select>

          <div className="cdl-view-toggle-btns" aria-label="View switcher">
            <button
              type="button"
              className={`cdl-view-toggle-btn ${viewMode === "table" ? "active" : ""}`}
              onClick={() => setViewMode("table")}
              title="Table view"
            >
              ☰ Table
            </button>
            <button
              type="button"
              className={`cdl-view-toggle-btn ${viewMode === "grid" ? "active" : ""}`}
              onClick={() => setViewMode("grid")}
              title="Grid view"
            >
              ⊞ Grid
            </button>
          </div>
        </div>
      </section>

      {/* 4. MAIN STUDIES CONTENT AREA */}
      {loading ? (
        <div className="cdl-table-container" style={{ padding: "16px 0" }}>
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="cdl-study-skeleton-row" />
          ))}
        </div>
      ) : processedStudies.length === 0 ? (
        <div className="cdl-studies-empty-box">
          <span className="cdl-studies-empty-icon">📁</span>
          <h3 style={{ margin: 0, fontSize: 18, color: "#0f172a" }}>
            {searchQuery || filterCohort !== "all"
              ? "No studies match your filter criteria"
              : "No research studies yet"}
          </h3>
          <p className="cdl-studies-empty-text">
            {searchQuery || filterCohort !== "all"
              ? "Try adjusting your search terms or clearing the active cohort filter."
              : "Create your first research study to aggregate and organize cardiac deformation analyses across subjects and trials."}
          </p>
          {searchQuery || filterCohort !== "all" ? (
            <button
              type="button"
              className="cdl-btn-view-study"
              onClick={() => {
                setSearchQuery("");
                setFilterCohort("all");
              }}
            >
              Reset Filters
            </button>
          ) : (
            <button
              type="button"
              className="cdl-btn-primary-action"
              onClick={() => setShowCreateModal(true)}
            >
              + Create Your First Study
            </button>
          )}
        </div>
      ) : viewMode === "table" ? (
        /* TABLE VIEW */
        <div className="cdl-table-container">
          <table className="cdl-studies-table">
            <thead>
              <tr>
                <th>Study Details</th>
                <th>Subject Code</th>
                <th>Analyses</th>
                <th>Status</th>
                <th>Created</th>
                <th>Last Updated</th>
                <th style={{ textAlign: "right" }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {paginatedStudies.map((study) => {
                const count = study.analysis_ids ? study.analysis_ids.length : 0;
                const isMulti = count > 1;

                return (
                  <tr key={study.id}>
                    <td>
                      <div className="cdl-cell-study-title">
                        <div className="cdl-cell-avatar">📁</div>
                        <div className="cdl-cell-info">
                          <Link
                            to={`/studies/${study.id}`}
                            className="cdl-cell-name-link"
                          >
                            {study.title}
                          </Link>
                          {study.description ? (
                            <span className="cdl-cell-desc-snippet" title={study.description}>
                              {study.description}
                            </span>
                          ) : (
                            <span className="cdl-cell-id-code">ID: {study.id.slice(0, 8)}...</span>
                          )}
                        </div>
                      </div>
                    </td>

                    <td>
                      {study.subject_code ? (
                        <span className="cdl-subject-tag">{study.subject_code}</span>
                      ) : (
                        <span style={{ color: "#94a3b8", fontSize: 12 }}>Unassigned</span>
                      )}
                    </td>

                    <td>
                      <span className="cdl-analysis-count-pill">
                        <span>📊</span>
                        <span>{count}</span>
                      </span>
                    </td>

                    <td>
                      {count > 0 ? (
                        <span
                          className={`cdl-status-badge ${
                            isMulti ? "status-multi" : "status-active"
                          }`}
                        >
                          {isMulti ? "Multi-Session" : "Active Cohort"}
                        </span>
                      ) : (
                        <span className="cdl-status-badge status-empty">
                          Pending Runs
                        </span>
                      )}
                    </td>

                    <td style={{ color: "#64748b", fontSize: 13 }}>
                      {formatDate(study.created_at)}
                    </td>

                    <td style={{ color: "#64748b", fontSize: 13 }}>
                      {formatDate(study.updated_at || study.created_at)}
                    </td>

                    <td>
                      <div className="cdl-table-actions">
                        <Link
                          to={`/studies/${study.id}`}
                          className="cdl-btn-view-study"
                        >
                          Open Study →
                        </Link>
                        <button
                          type="button"
                          className="cdl-btn-table-icon"
                          onClick={(e) => handleStartEdit(e, study)}
                          title="Edit study metadata"
                        >
                          ✏️
                        </button>
                        <button
                          type="button"
                          className="cdl-btn-table-icon btn-delete"
                          onClick={(e) => handleDelete(e, study.id, study.title)}
                          title="Delete research study"
                        >
                          🗑️
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        /* GRID VIEW */
        <div className="cdl-studies-grid-view">
          {paginatedStudies.map((study) => {
            const count = study.analysis_ids ? study.analysis_ids.length : 0;
            const isMulti = count > 1;

            return (
              <div key={study.id} className="cdl-study-grid-card">
                <div>
                  <div className="cdl-card-top-row">
                    <div className="cdl-card-title-group">
                      {study.subject_code ? (
                        <span className="cdl-subject-tag">{study.subject_code}</span>
                      ) : (
                        <span style={{ color: "#94a3b8", fontSize: 11.5 }}>
                          ID: {study.id.slice(0, 8)}...
                        </span>
                      )}
                      <Link
                        to={`/studies/${study.id}`}
                        className="cdl-card-title"
                        title={study.title}
                      >
                        {study.title}
                      </Link>
                    </div>

                    {count > 0 ? (
                      <span
                        className={`cdl-status-badge ${
                          isMulti ? "status-multi" : "status-active"
                        }`}
                      >
                        {isMulti ? "Multi" : "Active"}
                      </span>
                    ) : (
                      <span className="cdl-status-badge status-empty">Pending</span>
                    )}
                  </div>

                  {study.description && (
                    <p className="cdl-card-desc">{study.description}</p>
                  )}
                </div>

                <div className="cdl-card-meta-box">
                  <span>📊 {count} {count === 1 ? "analysis" : "analyses"} linked</span>
                  <span>Updated: {formatDate(study.updated_at || study.created_at)}</span>
                </div>

                <div className="cdl-card-actions-row">
                  <div style={{ display: "flex", gap: 6 }}>
                    <button
                      type="button"
                      className="cdl-btn-table-icon"
                      onClick={(e) => handleStartEdit(e, study)}
                      title="Edit metadata"
                    >
                      ✏️
                    </button>
                    <button
                      type="button"
                      className="cdl-btn-table-icon btn-delete"
                      onClick={(e) => handleDelete(e, study.id, study.title)}
                      title="Delete study"
                    >
                      🗑️
                    </button>
                  </div>
                  <Link
                    to={`/studies/${study.id}`}
                    className="cdl-btn-view-study"
                  >
                    Open Study →
                  </Link>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* 5. PAGINATION CONTROLS */}
      {processedStudies.length > itemsPerPage && (
        <section className="cdl-pagination-bar" aria-label="Pagination">
          <div>
            Showing{" "}
            <strong>
              {(currentPage - 1) * itemsPerPage + 1}–
              {Math.min(currentPage * itemsPerPage, processedStudies.length)}
            </strong>{" "}
            of <strong>{processedStudies.length}</strong> studies
          </div>

          <div className="cdl-page-buttons">
            <button
              type="button"
              className="cdl-page-btn"
              onClick={() => handlePageChange(currentPage - 1)}
              disabled={currentPage === 1}
            >
              ← Prev
            </button>

            {Array.from({ length: totalPages }, (_, i) => i + 1)
              .filter(
                (p) =>
                  p === 1 ||
                  p === totalPages ||
                  (p >= currentPage - 2 && p <= currentPage + 2)
              )
              .map((p, idx, arr) => {
                const prev = arr[idx - 1];
                return (
                  <span key={p} style={{ display: "inline-flex", alignItems: "center" }}>
                    {prev && p - prev > 1 && (
                      <span style={{ padding: "0 4px", color: "#94a3b8" }}>…</span>
                    )}
                    <button
                      type="button"
                      className={`cdl-page-btn ${currentPage === p ? "active" : ""}`}
                      onClick={() => handlePageChange(p)}
                    >
                      {p}
                    </button>
                  </span>
                );
              })}

            <button
              type="button"
              className="cdl-page-btn"
              onClick={() => handlePageChange(currentPage + 1)}
              disabled={currentPage === totalPages}
            >
              Next →
            </button>
          </div>
        </section>
      )}

      {/* CREATE STUDY MODAL */}
      {showCreateModal && (
        <div
          className="cdl-modal-backdrop"
          onClick={() => !creating && setShowCreateModal(false)}
          role="dialog"
          aria-modal="true"
        >
          <div className="cdl-modal-box" onClick={(e) => e.stopPropagation()}>
            <div className="cdl-modal-header">
              <h3>Create New Research Study</h3>
              <button
                type="button"
                className="cdl-modal-close"
                onClick={() => !creating && setShowCreateModal(false)}
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateSubmit}>
              <div className="cdl-modal-body">
                {createModalError && (
                  <div className="cdl-alert-banner cdl-alert-error" style={{ padding: "8px 12px" }}>
                    {createModalError}
                  </div>
                )}

                <div className="cdl-modal-form-group">
                  <label htmlFor="create-study-title">
                    Study Title <span style={{ color: "#ef4444" }}>*</span>
                  </label>
                  <input
                    id="create-study-title"
                    type="text"
                    className="cdl-modal-input"
                    placeholder="e.g. Apical 4-Chamber Cine Study 001"
                    required
                    value={createTitle}
                    onChange={(e) => setCreateTitle(e.target.value)}
                  />
                </div>

                <div className="cdl-modal-form-group">
                  <label htmlFor="create-subject-code">
                    Subject Code <span className="cdl-modal-field-hint">(optional pseudonym)</span>
                  </label>
                  <input
                    id="create-subject-code"
                    type="text"
                    className="cdl-modal-input"
                    placeholder="e.g. SUBJ-001 or ANONYMOUS-42"
                    value={createSubjectCode}
                    onChange={(e) => setCreateSubjectCode(e.target.value)}
                  />
                  <span className="cdl-modal-field-hint">
                    Do not enter real patient names or identifying medical record numbers.
                  </span>
                </div>

                <div className="cdl-modal-form-group">
                  <label htmlFor="create-study-desc">Description &amp; Protocol Notes</label>
                  <textarea
                    id="create-study-desc"
                    rows={3}
                    className="cdl-modal-textarea"
                    placeholder="Protocol notes, imaging modality, frame acquisition context..."
                    value={createDescription}
                    onChange={(e) => setCreateDescription(e.target.value)}
                  />
                </div>
              </div>

              <div className="cdl-modal-footer">
                <button
                  type="button"
                  className="cdl-btn-view-study"
                  onClick={() => setShowCreateModal(false)}
                  disabled={creating}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="cdl-btn-primary-action"
                  disabled={creating || !createTitle.trim()}
                >
                  {creating ? "Creating..." : "Save Study"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* EDIT STUDY MODAL */}
      {editingStudy && (
        <div
          className="cdl-modal-backdrop"
          onClick={() => !savingEdit && setEditingStudy(null)}
          role="dialog"
          aria-modal="true"
        >
          <div className="cdl-modal-box" onClick={(e) => e.stopPropagation()}>
            <div className="cdl-modal-header">
              <h3>Edit Research Study</h3>
              <button
                type="button"
                className="cdl-modal-close"
                onClick={() => !savingEdit && setEditingStudy(null)}
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleEditSubmit}>
              <div className="cdl-modal-body">
                {editModalError && (
                  <div className="cdl-alert-banner cdl-alert-error" style={{ padding: "8px 12px" }}>
                    {editModalError}
                  </div>
                )}

                <div className="cdl-modal-form-group">
                  <label htmlFor="edit-study-title">
                    Study Title <span style={{ color: "#ef4444" }}>*</span>
                  </label>
                  <input
                    id="edit-study-title"
                    type="text"
                    className="cdl-modal-input"
                    required
                    value={editTitle}
                    onChange={(e) => setEditTitle(e.target.value)}
                  />
                </div>

                <div className="cdl-modal-form-group">
                  <label htmlFor="edit-subject-code">Subject Code (optional)</label>
                  <input
                    id="edit-subject-code"
                    type="text"
                    className="cdl-modal-input"
                    value={editSubjectCode}
                    onChange={(e) => setEditSubjectCode(e.target.value)}
                  />
                </div>

                <div className="cdl-modal-form-group">
                  <label htmlFor="edit-study-desc">Description &amp; Protocol Notes</label>
                  <textarea
                    id="edit-study-desc"
                    rows={3}
                    className="cdl-modal-textarea"
                    value={editDescription}
                    onChange={(e) => setEditDescription(e.target.value)}
                  />
                </div>
              </div>

              <div className="cdl-modal-footer">
                <button
                  type="button"
                  className="cdl-btn-view-study"
                  onClick={() => setEditingStudy(null)}
                  disabled={savingEdit}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="cdl-btn-primary-action"
                  disabled={savingEdit || !editTitle.trim()}
                >
                  {savingEdit ? "Updating..." : "Update Study"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
