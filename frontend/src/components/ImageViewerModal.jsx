import { useEffect } from "react";

export default function ImageViewerModal({ isOpen, imageSrc, title, description, onClose }) {
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e) => {
      if (e.key === "Escape") {
        onClose();
      }
    };

    // Prevent background scrolling
    const originalOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", handleKeyDown);

    return () => {
      document.body.style.overflow = originalOverflow;
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen || !imageSrc) return null;

  return (
    <div
      className="image-modal-backdrop"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label={title || "Expanded image view"}
    >
      <div
        className="image-modal-content"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="image-modal-header">
          <div className="image-modal-titles">
            <h3 className="image-modal-title">{title}</h3>
            {description && <p className="image-modal-desc">{description}</p>}
          </div>
          <button
            className="image-modal-close-btn"
            onClick={onClose}
            aria-label="Close modal (Esc)"
            title="Close (Esc)"
          >
            ✕
          </button>
        </div>

        <div className="image-modal-body">
          <img
            src={imageSrc}
            alt={title}
            className="image-modal-img"
          />
        </div>

        <div className="image-modal-footer">
          <span className="image-modal-hint">Press <strong>Esc</strong> or click outside to dismiss</span>
          <a
            href={imageSrc}
            target="_blank"
            rel="noopener noreferrer"
            className="btn-modal-open-tab"
          >
            ↗ Open Original
          </a>
        </div>
      </div>
    </div>
  );
}

