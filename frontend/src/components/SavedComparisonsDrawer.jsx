import { useState, useEffect } from "react";
import { getComparisonHistory, deleteComparisonById } from "../services/api";

export default function SavedComparisonsDrawer({
  isOpen,
  onClose,
  onSelectComparison,
}) {
  const [comparisons, setComparisons] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [deletingId, setDeletingId] = useState(null);

  const fetchHistory = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getComparisonHistory();
      setComparisons(data || []);
    } catch (err) {
      setError(err.message || "Failed to load saved comparisons.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchHistory();
    }
  }, [isOpen]);

  const handleDelete = async (e, compId) => {
    e.stopPropagation();
    if (!window.confirm("Are you sure you want to delete this saved comparison?")) {
      return;
    }
    setDeletingId(compId);
    try {
      await deleteComparisonById(compId);
      setComparisons((prev) => prev.filter((c) => c.id !== compId));
    } catch (err) {
      alert(`Failed to delete comparison: ${err.message}`);
    } finally {
      setDeletingId(null);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="roi-preview-modal-backdrop" onClick={onClose}>
      <div
        className="roi-preview-modal-dialog saved-drawer-dialog"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="roi-preview-modal-header">
          <div className="modal-title-group">
            <h3>Saved Analysis Comparisons</h3>
            <span className="roi-tracked-badge">{comparisons.length} SAVED</span>
          </div>
          <button
            type="button"
            className="roi-modal-close-btn"
            onClick={onClose}
            aria-label="Close"
          >
            &times;
          </button>
        </div>

        <div className="roi-preview-modal-body" style={{ maxHeight: "65vh", overflowY: "auto" }}>
          {loading && (
            <div className="status-banner loading">
              <span className="spinner"></span> Loading saved comparisons...
            </div>
          )}

          {error && (
            <div className="status-banner error">
              <strong>Error:</strong> {error}
            </div>
          )}

          {!loading && comparisons.length === 0 && (
            <div className="saved-empty-state" style={{ textAlign: "center", padding: "30px 20px" }}>
              <span style={{ fontSize: 32, display: "block", marginBottom: 10 }}>📁</span>
              <p style={{ color: "var(--text-muted)", fontSize: 14 }}>
                No saved comparisons found. Select 2 to 5 analyses and click "Save Comparison" to record your findings.
              </p>
            </div>
          )}

          <div className="saved-comparisons-list" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {comparisons.map((c) => (
              <div
                key={c.id}
                className="saved-comp-card"
                onClick={() => {
                  onSelectComparison(c);
                  onClose();
                }}
              >
                <div className="saved-comp-card-top">
                  <div>
                    <h4 className="saved-comp-title">{c.title}</h4>
                    <span className="saved-comp-date">
                      {new Date(c.created_at).toLocaleString()} &bull; {c.analysis_count} analyses
                    </span>
                  </div>
                  <button
                    type="button"
                    className="btn-danger-sm"
                    onClick={(e) => handleDelete(e, c.id)}
                    disabled={deletingId === c.id}
                    title="Delete saved comparison"
                  >
                    {deletingId === c.id ? "..." : "Delete"}
                  </button>
                </div>

                {c.notes && (
                  <p className="saved-comp-notes">
                    <strong>Notes:</strong> {c.notes}
                  </p>
                )}

                <div className="saved-comp-ids">
                  {c.analysis_ids.map((id, idx) => (
                    <span key={id} className="comp-id-pill">
                      Analysis {idx + 1}: <code>{id.slice(0, 8)}</code>
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="roi-preview-modal-footer">
          <button type="button" className="btn-secondary" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

