export default function SectionNav() {
  const sections = [
    { id: "section-overview", label: "Overview" },
    { id: "section-qc", label: "Quality Control" },
    { id: "section-motion", label: "Motion" },
    { id: "section-strain", label: "Strain" },
    { id: "section-directional", label: "Directional" },
    { id: "section-advanced", label: "Advanced Metrics" },
    { id: "section-fingerprint", label: "Fingerprint" },
    { id: "section-interpretation", label: "Interpretation" },
    { id: "section-methodology", label: "Methodology" },
  ];

  const handleScroll = (e, id) => {
    e.preventDefault();
    const elem = document.getElementById(id);
    if (elem) {
      elem.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  };

  return (
    <nav className="dashboard-section-nav" aria-label="Analysis sections">
      <div className="section-nav-pill-list">
        {sections.map((s) => (
          <a
            key={s.id}
            href={`#${s.id}`}
            className="section-nav-pill"
            onClick={(e) => handleScroll(e, s.id)}
          >
            {s.label}
          </a>
        ))}
      </div>
    </nav>
  );
}

