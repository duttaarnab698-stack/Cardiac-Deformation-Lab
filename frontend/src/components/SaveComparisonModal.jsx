import { useState } from "react";

export default function SaveComparisonModal({
  isOpen,
  onClose,
  onSave,
  loading,
  defaultTitle = "",
}) {
  const [title, setTitle] = useState(defaultTitle);
  const [notes, setNotes] = useState("");

  if (!isOpen) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    onSave({ title: title.trim() || defaultTitle, notes: notes.trim() });
  };

  return (
    <div className="roi-preview-modal-backdrop" onClick={onClose}>
      <div
        className="roi-preview-modal-dialog save-comp-dialog"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="roi-preview-modal-header">
          <div className="modal-title-group">
            <h3>Save Analysis Comparison</h3>
            <span className="roi-tracked-badge">RESEARCH RECORD</span>
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

        <form onSubmit={handleSubmit}>
          <div className="roi-preview-modal-body">
            <div className="form-group" style={{ marginBottom: 16 }}>
              <label htmlFor="comp-title" style={{ display: "block", marginBottom: 6, fontWeight: 600 }}>
                Comparison Title:
              </label>
              <input
                id="comp-title"
                type="text"
                className="study-input"
                style={{ width: "100%" }}
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder={defaultTitle || "e.g., Pre vs Post Exercise Deformation"}
              />
            </div>

            <div className="form-group">
              <label htmlFor="comp-notes" style={{ display: "block", marginBottom: 6, fontWeight: 600 }}>
                Research Notes (Optional):
              </label>
              <textarea
                id="comp-notes"
                className="study-input"
                style={{ width: "100%", height: 80, resize: "vertical" }}
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Observation notes, acquisition context, or experimental conditions..."
              />
            </div>
          </div>

          <div className="roi-preview-modal-footer" style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
            <button type="button" className="btn-secondary" onClick={onClose} disabled={loading}>
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={loading}>
              {loading ? "Saving Comparison..." : "Save Comparison"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

