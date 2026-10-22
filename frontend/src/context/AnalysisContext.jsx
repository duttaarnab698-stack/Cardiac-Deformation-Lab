import { createContext, useContext, useState, useEffect } from "react";

const AnalysisContext = createContext(null);

export function AnalysisProvider({ children }) {
  const [latestAnalysisResult, setLatestAnalysisResult] = useState(null);
  const [latestTemporalResult, setLatestTemporalResult] = useState(null);
  const [analysisHistoryCount, setAnalysisHistoryCount] = useState(0);
  const [lastAnalysisTimestamp, setLastAnalysisTimestamp] = useState(null);

  // Theme state: "light" or "dark" (persisted in localStorage)
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem("cdl_theme") || "light";
  });

  useEffect(() => {
    localStorage.setItem("cdl_theme", theme);
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === "light" ? "dark" : "light"));
  };

  const handleSetLatestAnalysisResult = (result) => {
    setLatestAnalysisResult(result);
    setAnalysisHistoryCount((prev) => prev + 1);
    setLastAnalysisTimestamp(new Date().toLocaleTimeString());
  };

  const handleSetLatestTemporalResult = (result) => {
    setLatestTemporalResult(result);
    setAnalysisHistoryCount((prev) => prev + 1);
    setLastAnalysisTimestamp(new Date().toLocaleTimeString());
  };

  const clearResults = () => {
    setLatestAnalysisResult(null);
    setLatestTemporalResult(null);
  };

  return (
    <AnalysisContext.Provider
      value={{
        latestAnalysisResult,
        setLatestAnalysisResult: handleSetLatestAnalysisResult,
        latestTemporalResult,
        setLatestTemporalResult: handleSetLatestTemporalResult,
        analysisHistoryCount,
        lastAnalysisTimestamp,
        clearResults,
        theme,
        setTheme,
        toggleTheme,
      }}
    >
      {children}
    </AnalysisContext.Provider>
  );
}

export function useAnalysis() {
  const context = useContext(AnalysisContext);
  if (!context) {
    throw new Error("useAnalysis must be used within an AnalysisProvider");
  }
  return context;
}

