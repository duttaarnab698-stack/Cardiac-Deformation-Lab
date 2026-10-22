export const API_BASE_URL = "http://127.0.0.1:8000";

export function getStoredAuthToken() {
  return localStorage.getItem("cardiac_lab_token");
}

export function setStoredAuthToken(token) {
  if (token) {
    localStorage.setItem("cardiac_lab_token", token);
  } else {
    localStorage.removeItem("cardiac_lab_token");
  }
}

/**
 * Centralized authenticated fetch wrapper that injects Authorization: Bearer <token>
 * and handles 401 session expiration by dispatching an unauthorized event.
 */
export async function authFetch(url, options = {}) {
  const token = getStoredAuthToken();
  const headers = new Headers(options.headers || {});

  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const mergedOptions = {
    ...options,
    headers,
  };

  const response = await fetch(url, mergedOptions);

  if (response.status === 401) {
    if (typeof window !== "undefined") {
      window.dispatchEvent(new CustomEvent("cardiac-auth-unauthorized"));
    }
  }

  return response;
}

/**
 * Upload an image file to the FastAPI backend.
 * @param {File} file
 * @returns {Promise<{message: string, filename: string, saved_filename: string, path: string}>}
 */
export async function uploadImage(file) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await authFetch(`${API_BASE_URL}/api/upload/image`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(
      errorData?.detail || `Upload failed with status code ${response.status}`
    );
  }

  return await response.json();
}

/**
 * Run cardiac strain and deformation analysis between two uploaded images.
 * @param {string} image1Filename
/**
 * Send image filenames to FastAPI backend to compute strain and deformation.
 * Supports optional spatial calibration (pixelSpacingX, pixelSpacingY, unit).
 * @param {string} image1Filename
 * @param {string} image2Filename
 * @param {object} [calibration] - Optional { pixel_spacing_x, pixel_spacing_y, unit }
 * @param {object} [roi] - Optional { enabled, type, coordinates }
 * @returns {Promise<object>}
 */
export async function analyzeStrain(image1Filename, image2Filename, calibration = null, roi = null) {
  const params = new URLSearchParams({
    image1_filename: image1Filename,
    image2_filename: image2Filename,
  });

  if (calibration && calibration.enabled) {
    if (calibration.pixel_spacing_x) {
      params.append("pixel_spacing_x", calibration.pixel_spacing_x);
    }
    if (calibration.pixel_spacing_y) {
      params.append("pixel_spacing_y", calibration.pixel_spacing_y);
    }
    if (calibration.unit) {
      params.append("unit", calibration.unit);
    }
  }

  if (roi && roi.enabled) {
    params.append("roi", JSON.stringify(roi));
  }

  const response = await authFetch(
    `${API_BASE_URL}/api/analysis/strain?${params.toString()}`,
    {
      method: "POST",
    }
  );

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(
      errorData?.detail || `Analysis failed with status code ${response.status}`
    );
  }

  return await response.json();
}

/**
 * Convert backend output image path to browser-accessible URL.
 * @param {string} outputPath
 * @returns {string|null}
 */
export const getOutputUrl = (outputPath) => {
  if (!outputPath) return null;

  const filename = outputPath
    .replace(/\\/g, "/")
    .split("/")
    .pop();

  return `${API_BASE_URL}/outputs/${filename}`;
};

/**
 * Run temporal strain analysis across an array of uploaded image filenames.
 * Supports optional spatial calibration (pixelSpacingX, pixelSpacingY, unit).
 * @param {string[]} filenames
 * @param {object} [calibration] - Optional { pixel_spacing_x, pixel_spacing_y, unit }
 * @param {object} [roi] - Optional { enabled, type, coordinates }
 * @returns {Promise<object>}
 */
export async function analyzeTemporalStrain(filenames, calibration = null, roi = null) {
  const params = new URLSearchParams();
  filenames.forEach((fn) => params.append("filenames", fn));

  if (calibration && calibration.enabled) {
    if (calibration.pixel_spacing_x) {
      params.append("pixel_spacing_x", calibration.pixel_spacing_x);
    }
    if (calibration.pixel_spacing_y) {
      params.append("pixel_spacing_y", calibration.pixel_spacing_y);
    }
    if (calibration.unit) {
      params.append("unit", calibration.unit);
    }
  }

  if (roi && roi.enabled) {
    params.append("roi", JSON.stringify(roi));
  }

  const response = await authFetch(
    `${API_BASE_URL}/api/analysis/temporal-strain?${params.toString()}`,
    {
      method: "POST",
    }
  );

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(
      errorData?.detail ||
        `Temporal strain analysis failed with status code ${response.status}`
    );
  }

  return await response.json();
}

/**
 * Generate preview of ROI tracking across temporal frames.
 * @param {string[]} filenames
 * @param {object} roi - { enabled, type, coordinates, mode }
 * @returns {Promise<object>}
 */
export async function previewROITracking(filenames, roi) {
  const params = new URLSearchParams();
  filenames.forEach((fn) => params.append("filenames", fn));
  params.append("roi", JSON.stringify(roi));

  const response = await authFetch(
    `${API_BASE_URL}/api/analysis/roi/track-preview?${params.toString()}`,
    {
      method: "POST",
    }
  );

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(
      errorData?.detail ||
        `ROI tracking preview failed with status code ${response.status}`
    );
  }

  return await response.json();
}

/**
 * Check backend health status (/health).
 * @returns {Promise<boolean>}
 */
export async function checkBackendHealth() {
  try {
    const response = await authFetch(`${API_BASE_URL}/health`, { method: "GET" });
    if (!response.ok) return false;
    const data = await response.json();
    return data.status === "healthy";
  } catch {
    return false;
  }
}

/**
 * Retrieve all analysis history records from the backend.
 * @returns {Promise<Array<object>>}
 */
export async function getAnalysisHistory() {
  const response = await authFetch(`${API_BASE_URL}/api/history`, {
    method: "GET",
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(
      errorData?.detail || `Failed to fetch history (Status ${response.status})`
    );
  }

  return await response.json();
}

/**
 * Retrieve a specific analysis record by ID.
 * @param {string} analysisId
 * @returns {Promise<object>}
 */
export async function getAnalysisHistoryById(analysisId) {
  const response = await authFetch(`${API_BASE_URL}/api/history/${analysisId}`, {
    method: "GET",
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(
      errorData?.detail || `Failed to fetch analysis record (Status ${response.status})`
    );
  }

  return await response.json();
}

export const getHistory = getAnalysisHistory;
export const getHistoryById = getAnalysisHistoryById;

/**
 * Delete a specific analysis record by ID.
 * @param {string} analysisId
 * @returns {Promise<object>}
 */
export async function deleteAnalysisHistoryById(analysisId) {
  const response = await authFetch(`${API_BASE_URL}/api/history/${analysisId}`, {
    method: "DELETE",
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(
      errorData?.detail || `Failed to delete analysis record (Status ${response.status})`
    );
  }

  return await response.json();
}

/**
 * Clear all analysis history records.
 * @returns {Promise<object>}
 */
export async function clearAnalysisHistory() {
  const response = await authFetch(`${API_BASE_URL}/api/history`, {
    method: "DELETE",
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(
      errorData?.detail || `Failed to clear history (Status ${response.status})`
    );
  }

  return await response.json();
}

/**
 * Generate a PDF summary report for a given analysis record.
 * @param {string} analysisId
 * @returns {Promise<{message: string, analysis_id: string, report_filename: string, report_path: string, url: string}>}
 */
export async function generateAnalysisReport(analysisId) {
  const response = await authFetch(`${API_BASE_URL}/api/reports/${analysisId}`, {
    method: "POST",
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(
      errorData?.detail || `Failed to generate report (Status ${response.status})`
    );
  }

  return await response.json();
}

/**
 * Convert a backend report path or URL into a full browser URL.
 * @param {string} reportUrlOrFilename
 * @returns {string}
 */
export function getReportDownloadUrl(reportUrlOrFilename) {
  if (!reportUrlOrFilename) return "";
  if (reportUrlOrFilename.startsWith("http")) return reportUrlOrFilename;
  const clean = reportUrlOrFilename.replace(/\\/g, "/");
  const filename = clean.split("/").pop();
  return `${API_BASE_URL}/reports/${filename}`;
}

/**
 * Upload a cardiac video (.mp4, .avi, .mov, .mkv, .webm) to the backend.
 * @param {File} file
 * @returns {Promise<{message: string, filename: string, saved_filename: string, path: string}>}
 */
export async function uploadVideo(file) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await authFetch(`${API_BASE_URL}/api/video/upload`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(
      errorData?.detail || `Video upload failed with status code ${response.status}`
    );
  }

  return await response.json();
}

/**
 * Fetch video technical metadata (resolution, fps, duration, frames).
 * @param {string} filename
 * @returns {Promise<{filename: string, width: number, height: number, fps: number, total_frames: number, duration_seconds: number}>}
 */
export async function getVideoInfo(filename) {
  const response = await authFetch(`${API_BASE_URL}/api/video/info/${encodeURIComponent(filename)}`, {
    method: "GET",
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(
      errorData?.detail || `Failed to fetch video information (Status ${response.status})`
    );
  }

  return await response.json();
}

/**
 * Extract frames from an uploaded video.
 * @param {string} filename
 * @param {number} frameInterval
 * @param {number} maxFrames
 * @returns {Promise<{message: string, video: string, frame_count: number, frames: string[], relative_dir: string}>}
 */
export async function extractVideoFrames(filename, frameInterval = 1, maxFrames = 50) {
  const response = await authFetch(`${API_BASE_URL}/api/video/extract-frames`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      filename,
      frame_interval: Number(frameInterval),
      max_frames: Number(maxFrames),
    }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(
      errorData?.detail || `Frame extraction failed (Status ${response.status})`
    );
  }

  return await response.json();
}

/**
 * Get the static URL for an uploaded or extracted frame image.
 * @param {string} filename
 * @returns {string}
 */
export function getFrameImageUrl(filename) {
  if (!filename) return "";
  const clean = filename.replace(/\\/g, "/").split("/").pop();
  return `${API_BASE_URL}/uploads/${clean}`;
}

/**
 * Create a new cardiac motion study.
 * @param {{title: string, subject_code?: string, description?: string}} payload
 * @returns {Promise<object>}
 */
export async function createStudy(payload) {
  const response = await authFetch(`${API_BASE_URL}/api/studies`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(
      errorData?.detail || `Failed to create study (Status ${response.status})`
    );
  }

  return await response.json();
}

/**
 * Fetch all studies.
 * @returns {Promise<Array<object>>}
 */
export async function getStudies() {
  const response = await authFetch(`${API_BASE_URL}/api/studies`, {
    method: "GET",
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(
      errorData?.detail || `Failed to fetch studies (Status ${response.status})`
    );
  }

  return await response.json();
}

/**
 * Fetch a specific study by ID.
 * @param {string} studyId
 * @param {boolean} includeAnalyses
 * @returns {Promise<object>}
 */
export async function getStudy(studyId, includeAnalyses = true) {
  const response = await authFetch(
    `${API_BASE_URL}/api/studies/${encodeURIComponent(studyId)}?include_analyses=${Boolean(includeAnalyses)}`,
    { method: "GET" }
  );

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(
      errorData?.detail || `Failed to fetch study details (Status ${response.status})`
    );
  }

  return await response.json();
}

/**
 * Update an existing study.
 * @param {string} studyId
 * @param {{title?: string, subject_code?: string, description?: string}} payload
 * @returns {Promise<object>}
 */
export async function updateStudy(studyId, payload) {
  const response = await authFetch(`${API_BASE_URL}/api/studies/${encodeURIComponent(studyId)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(
      errorData?.detail || `Failed to update study (Status ${response.status})`
    );
  }

  return await response.json();
}

/**
 * Delete a study record (does not delete underlying analyses).
 * @param {string} studyId
 * @returns {Promise<object>}
 */
export async function deleteStudy(studyId) {
  const response = await authFetch(`${API_BASE_URL}/api/studies/${encodeURIComponent(studyId)}`, {
    method: "DELETE",
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(
      errorData?.detail || `Failed to delete study (Status ${response.status})`
    );
  }

  return await response.json();
}

/**
 * Link an analysis to a study.
 * @param {string} studyId
 * @param {string} analysisId
 * @returns {Promise<object>}
 */
export async function addAnalysisToStudy(studyId, analysisId) {
  const response = await authFetch(
    `${API_BASE_URL}/api/studies/${encodeURIComponent(studyId)}/analyses/${encodeURIComponent(analysisId)}`,
    { method: "POST" }
  );

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(
      errorData?.detail || `Failed to link analysis to study (Status ${response.status})`
    );
  }

  return await response.json();
}

/**
 * Unlink an analysis from a study.
 * @param {string} studyId
 * @param {string} analysisId
 * @returns {Promise<object>}
 */
export async function removeAnalysisFromStudy(studyId, analysisId) {
  const response = await authFetch(
    `${API_BASE_URL}/api/studies/${encodeURIComponent(studyId)}/analyses/${encodeURIComponent(analysisId)}`,
    { method: "DELETE" }
  );

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(
      errorData?.detail || `Failed to unlink analysis from study (Status ${response.status})`
    );
  }

  return await response.json();
}

/**
 * Compare 2 to 5 analyses by ID.
 * @param {string[]} analysisIds
 * @returns {Promise<object>}
 */
export async function compareAnalyses(analysisIds) {
  const response = await authFetch(`${API_BASE_URL}/api/comparison`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ analysis_ids: analysisIds }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(
      errorData?.detail || `Analysis comparison failed (Status ${response.status})`
    );
  }

  return await response.json();
}

/**
 * Save an analysis comparison record.
 * @param {object} payload - { analysis_ids, title, notes, comparison }
 * @returns {Promise<object>}
 */
export async function saveComparison(payload) {
  const response = await authFetch(`${API_BASE_URL}/api/comparison/save`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(
      errorData?.detail || `Failed to save comparison (Status ${response.status})`
    );
  }

  return await response.json();
}

/**
 * Retrieve all saved comparisons.
 * @returns {Promise<object[]>}
 */
export async function getComparisonHistory() {
  const response = await authFetch(`${API_BASE_URL}/api/comparison/history`, {
    method: "GET",
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(
      errorData?.detail || `Failed to fetch comparison history (Status ${response.status})`
    );
  }

  return await response.json();
}

/**
 * Retrieve a specific saved comparison by ID.
 * @param {string} comparisonId
 * @returns {Promise<object>}
 */
export async function getComparisonById(comparisonId) {
  const response = await authFetch(
    `${API_BASE_URL}/api/comparison/history/${encodeURIComponent(comparisonId)}`,
    { method: "GET" }
  );

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(
      errorData?.detail || `Failed to fetch comparison (Status ${response.status})`
    );
  }

  return await response.json();
}

/**
 * Delete a saved comparison by ID.
 * @param {string} comparisonId
 * @returns {Promise<object>}
 */
export async function deleteComparisonById(comparisonId) {
  const response = await authFetch(
    `${API_BASE_URL}/api/comparison/history/${encodeURIComponent(comparisonId)}`,
    { method: "DELETE" }
  );

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(
      errorData?.detail || `Failed to delete comparison (Status ${response.status})`
    );
  }

  return await response.json();
}

/**
 * Generate a PDF comparison report.
 * @param {object} payload - { comparison_id, analysis_ids, comparison, title }
 * @returns {Promise<object>}
 */
export async function generateComparisonReport(payload) {
  const response = await authFetch(`${API_BASE_URL}/api/comparison/report`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(
      errorData?.detail || `Failed to generate comparison report (Status ${response.status})`
    );
  }

  return await response.json();
}

/**
 * Retrieve computational quality control evaluation for an analysis.
 * @param {string} analysisId
 * @returns {Promise<object>}
 */
export async function getAnalysisQuality(analysisId) {
  const response = await authFetch(
    `${API_BASE_URL}/api/quality/${encodeURIComponent(analysisId)}`
  );

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(
      errorData?.detail || `Failed to fetch quality control data (Status ${response.status})`
    );
  }

  return await response.json();
}

/**
 * Re-evaluate computational quality control for an analysis.
 * @param {string} analysisId
 * @returns {Promise<object>}
 */
export async function computeAnalysisQuality(analysisId) {
  const response = await authFetch(
    `${API_BASE_URL}/api/quality/${encodeURIComponent(analysisId)}`,
    { method: "POST" }
  );

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(
      errorData?.detail || `Failed to evaluate quality control (Status ${response.status})`
    );
  }

  return await response.json();
}

/**
 * Retrieve longitudinal analysis summary for a study.
 * @param {string} studyId
 * @returns {Promise<object>}
 */
export async function getLongitudinalStudySummary(studyId) {
  const response = await authFetch(
    `${API_BASE_URL}/api/longitudinal/study/${encodeURIComponent(studyId)}`
  );

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(
      errorData?.detail || `Failed to fetch longitudinal summary (Status ${response.status})`
    );
  }

  return await response.json();
}

/**
 * Retrieve longitudinal timeline data for frontend charting.
 * @param {string} studyId
 * @returns {Promise<object>}
 */
export async function getLongitudinalStudyTimeline(studyId) {
  const response = await authFetch(
    `${API_BASE_URL}/api/longitudinal/study/${encodeURIComponent(studyId)}/timeline`
  );

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(
      errorData?.detail || `Failed to fetch longitudinal timeline (Status ${response.status})`
    );
  }

  return await response.json();
}

/**
 * Retrieve longitudinal metric trend summaries for a study.
 * @param {string} studyId
 * @returns {Promise<object>}
 */
export async function getLongitudinalStudyTrends(studyId) {
  const response = await authFetch(
    `${API_BASE_URL}/api/longitudinal/study/${encodeURIComponent(studyId)}/trends`
  );

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(
      errorData?.detail || `Failed to fetch longitudinal trends (Status ${response.status})`
    );
  }

  return await response.json();
}

/**
 * Generate a PDF longitudinal study report.
 * @param {string} studyId
 * @returns {Promise<object>}
 */
export async function generateLongitudinalReport(studyId) {
  const response = await authFetch(
    `${API_BASE_URL}/api/reports/longitudinal/${encodeURIComponent(studyId)}`,
    {
      method: "POST",
    }
  );

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(
      errorData?.detail || `Failed to generate longitudinal report (Status ${response.status})`
    );
  }

  return await response.json();
}

/**
 * Retrieve comprehensive advanced statistical analytics for a study.
 * @param {string} studyId
 * @param {string} scope - "full_image" | "roi"
 * @returns {Promise<object>}
 */
export async function getStudyStatistics(studyId, scope = "full_image") {
  const response = await authFetch(
    `${API_BASE_URL}/api/statistics/study/${encodeURIComponent(studyId)}?scope=${encodeURIComponent(scope)}`
  );

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(
      errorData?.detail || `Failed to fetch study statistics (Status ${response.status})`
    );
  }

  return await response.json();
}

/**
 * Retrieve metric correlation matrix for a study.
 * @param {string} studyId
 * @param {string} scope - "full_image" | "roi"
 * @returns {Promise<object>}
 */
export async function getStudyCorrelations(studyId, scope = "full_image") {
  const response = await authFetch(
    `${API_BASE_URL}/api/statistics/study/${encodeURIComponent(studyId)}/correlations?scope=${encodeURIComponent(scope)}`
  );

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(
      errorData?.detail || `Failed to fetch metric correlations (Status ${response.status})`
    );
  }

  return await response.json();
}

/**
 * Retrieve computational statistical outliers (1.5xIQR) for a study.
 * @param {string} studyId
 * @param {string} scope - "full_image" | "roi"
 * @returns {Promise<object>}
 */
export async function getStudyOutliers(studyId, scope = "full_image") {
  const response = await authFetch(
    `${API_BASE_URL}/api/statistics/study/${encodeURIComponent(studyId)}/outliers?scope=${encodeURIComponent(scope)}`
  );

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(
      errorData?.detail || `Failed to fetch study outliers (Status ${response.status})`
    );
  }

  return await response.json();
}

/**
 * Generate a PDF advanced research statistics report.
 * @param {string} studyId
 * @param {string} scope - "full_image" | "roi"
 * @returns {Promise<object>}
 */
export async function generateStatisticsReport(studyId, scope = "full_image") {
  const response = await authFetch(
    `${API_BASE_URL}/api/reports/statistics/${encodeURIComponent(studyId)}?scope=${encodeURIComponent(scope)}`,
    {
      method: "POST",
    }
  );

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(
      errorData?.detail || `Failed to generate statistics report (Status ${response.status})`
    );
  }

  return await response.json();
}

/**
 * Generate a new synthetic cardiac phantom dataset with ground truth.
 * @param {object} config
 * @returns {Promise<object>}
 */
export async function generateSyntheticDataset(config) {
  const response = await authFetch(`${API_BASE_URL}/api/synthetic/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(config),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(
      errorData?.detail || `Failed to generate synthetic dataset (Status ${response.status})`
    );
  }

  return await response.json();
}

/**
 * Retrieve metadata for a synthetic dataset.
 * @param {string} datasetId
 * @returns {Promise<object>}
 */
export async function getSyntheticDataset(datasetId) {
  const response = await authFetch(`${API_BASE_URL}/api/synthetic/${encodeURIComponent(datasetId)}`);

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(
      errorData?.detail || `Failed to fetch synthetic dataset (Status ${response.status})`
    );
  }

  return await response.json();
}

/**
 * Retrieve frame URLs for a synthetic dataset.
 * @param {string} datasetId
 * @returns {Promise<object>}
 */
export async function getSyntheticFrames(datasetId) {
  const response = await authFetch(`${API_BASE_URL}/api/synthetic/${encodeURIComponent(datasetId)}/frames`);

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(
      errorData?.detail || `Failed to fetch synthetic frames (Status ${response.status})`
    );
  }

  return await response.json();
}

/**
 * Retrieve ground truth metadata summary for a synthetic dataset.
 * @param {string} datasetId
 * @returns {Promise<object>}
 */
export async function getSyntheticGroundTruth(datasetId) {
  const response = await authFetch(`${API_BASE_URL}/api/synthetic/${encodeURIComponent(datasetId)}/ground-truth`);

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(
      errorData?.detail || `Failed to fetch ground truth summary (Status ${response.status})`
    );
  }

  return await response.json();
}

/**
 * Run algorithmic motion estimation & strain calculation against ground truth.
 * @param {string} datasetId
 * @returns {Promise<object>}
 */
export async function validateSyntheticDataset(datasetId) {
  const response = await authFetch(`${API_BASE_URL}/api/synthetic/${encodeURIComponent(datasetId)}/validate`, {
    method: "POST",
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(
      errorData?.detail || `Validation benchmark failed (Status ${response.status})`
    );
  }

  return await response.json();
}

/**
 * Run multi-parameter robustness sweep across noise and blur levels.
 * @param {string} datasetId
 * @returns {Promise<object>}
 */
export async function runRobustnessSweep(datasetId) {
  const response = await authFetch(`${API_BASE_URL}/api/synthetic/${encodeURIComponent(datasetId)}/robustness`, {
    method: "POST",
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(
      errorData?.detail || `Robustness sweep failed (Status ${response.status})`
    );
  }

  return await response.json();
}

/**
 * Retrieve historical synthetic validation benchmark runs.
 * @returns {Promise<Array>}
 */
export async function getValidationHistory() {
  const response = await authFetch(`${API_BASE_URL}/api/synthetic/validation/history`);

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(
      errorData?.detail || `Failed to fetch validation history (Status ${response.status})`
    );
  }

  return await response.json();
}

/**
 * Generate a PDF validation benchmark report.
 * @param {string} datasetId
 * @returns {Promise<object>}
 */
export async function generateValidationReport(datasetId) {
  const response = await authFetch(`${API_BASE_URL}/api/reports/validation/${encodeURIComponent(datasetId)}`, {
    method: "POST",
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(
      errorData?.detail || `Failed to generate validation report (Status ${response.status})`
    );
  }

  return await response.json();
}

/**
 * Create a new manual reference annotation.
 * @param {object} payload
 * @returns {Promise<object>}
 */
export async function createAnnotation(payload) {
  const response = await authFetch(`${API_BASE_URL}/api/annotations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(
      errorData?.detail || `Failed to create annotation (Status ${response.status})`
    );
  }

  return await response.json();
}

/**
 * Retrieve annotations matching filters.
 * @param {object} [params]
 * @returns {Promise<Array>}
 */
export async function getAnnotations(params = {}) {
  const query = new URLSearchParams();
  if (params.analysis_id) query.append("analysis_id", params.analysis_id);
  if (params.study_id) query.append("study_id", params.study_id);
  if (params.image_filename) query.append("image_filename", params.image_filename);
  if (params.annotation_type) query.append("annotation_type", params.annotation_type);

  const qs = query.toString() ? `?${query.toString()}` : "";
  const response = await authFetch(`${API_BASE_URL}/api/annotations${qs}`);

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(
      errorData?.detail || `Failed to fetch annotations (Status ${response.status})`
    );
  }

  return await response.json();
}

/**
 * Retrieve annotations for a specific image filename.
 * @param {string} imageFilename
 * @returns {Promise<Array>}
 */
export async function getImageAnnotations(imageFilename) {
  const response = await authFetch(`${API_BASE_URL}/api/annotations/image/${encodeURIComponent(imageFilename)}`);

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(
      errorData?.detail || `Failed to fetch image annotations (Status ${response.status})`
    );
  }

  return await response.json();
}

/**
 * Retrieve annotations for a specific analysis ID.
 * @param {string} analysisId
 * @returns {Promise<Array>}
 */
export async function getAnalysisAnnotations(analysisId) {
  const response = await authFetch(`${API_BASE_URL}/api/annotations/analysis/${encodeURIComponent(analysisId)}`);

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(
      errorData?.detail || `Failed to fetch analysis annotations (Status ${response.status})`
    );
  }

  return await response.json();
}

/**
 * Retrieve a single annotation by ID.
 * @param {string} annotationId
 * @returns {Promise<object>}
 */
export async function getAnnotationById(annotationId) {
  const response = await authFetch(`${API_BASE_URL}/api/annotations/${encodeURIComponent(annotationId)}`);

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(
      errorData?.detail || `Failed to fetch annotation (Status ${response.status})`
    );
  }

  return await response.json();
}

/**
 * Update an existing annotation.
 * @param {string} annotationId
 * @param {object} payload
 * @returns {Promise<object>}
 */
export async function updateAnnotation(annotationId, payload) {
  const response = await authFetch(`${API_BASE_URL}/api/annotations/${encodeURIComponent(annotationId)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(
      errorData?.detail || `Failed to update annotation (Status ${response.status})`
    );
  }

  return await response.json();
}

/**
 * Delete a single annotation.
 * @param {string} annotationId
 * @returns {Promise<object>}
 */
export async function deleteAnnotation(annotationId) {
  const response = await authFetch(`${API_BASE_URL}/api/annotations/${encodeURIComponent(annotationId)}`, {
    method: "DELETE",
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(
      errorData?.detail || `Failed to delete annotation (Status ${response.status})`
    );
  }

  return await response.json();
}

/**
 * Convert a polygon/contour annotation into an ROI object.
 * @param {string} annotationId
 * @returns {Promise<object>}
 */
export async function convertAnnotationToRoi(annotationId) {
  const response = await authFetch(`${API_BASE_URL}/api/annotations/${encodeURIComponent(annotationId)}/to-roi`, {
    method: "POST",
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(
      errorData?.detail || `Failed to convert annotation to ROI (Status ${response.status})`
    );
  }

  return await response.json();
}

/**
 * Export all annotations for an analysis as a JSON package.
 * @param {string} analysisId
 * @returns {Promise<object>}
 */
export async function exportAnnotations(analysisId) {
  const response = await authFetch(`${API_BASE_URL}/api/annotations/analysis/${encodeURIComponent(analysisId)}/export`);

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(
      errorData?.detail || `Failed to export annotations (Status ${response.status})`
    );
  }

  return await response.json();
}

/**
 * Import an annotation JSON package.
 * @param {object} packageData
 * @returns {Promise<object>}
 */
export async function importAnnotations(packageData) {
  const response = await authFetch(`${API_BASE_URL}/api/annotations/import`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(packageData),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(
      errorData?.detail || `Failed to import annotations (Status ${response.status})`
    );
  }

  return await response.json();
}

/**
 * Run real-image benchmark comparing analysis results vs manual annotations.
 * @param {string} analysisId
 * @returns {Promise<object>}
 */
export async function runRealImageValidation(analysisId) {
  const response = await authFetch(`${API_BASE_URL}/api/validation/real/${encodeURIComponent(analysisId)}`, {
    method: "POST",
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(
      errorData?.detail || `Real validation benchmark failed (Status ${response.status})`
    );
  }

  return await response.json();
}

/**
 * Generate a PDF report for real-image benchmark results.
 * @param {string} analysisId
 * @returns {Promise<object>}
 */
export async function generateRealValidationReport(analysisId) {
  const response = await authFetch(`${API_BASE_URL}/api/reports/real-validation/${encodeURIComponent(analysisId)}`, {
    method: "POST",
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(
      errorData?.detail || `Failed to generate real validation report (Status ${response.status})`
    );
  }

  return await response.json();
}

/* ==========================================================================
   AUTHENTICATION & RESEARCH WORKSPACE API SERVICES
   ========================================================================== */

/**
 * Authenticate with email and password to receive JWT access token.
 * @param {string} email
 * @param {string} password
 * @returns {Promise<{access_token: string, token_type: string, user: object, message: string}>}
 */
export async function loginUser(email, password) {
  const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(errorData?.detail || `Login failed (Status ${response.status})`);
  }

  const data = await response.json();
  if (data.access_token) {
    setStoredAuthToken(data.access_token);
  }
  return data;
}

/**
 * Register a new user account.
 * @param {string} name
 * @param {string} email
 * @param {string} password
 * @param {string} [role="researcher"]
 * @returns {Promise<{message: string, user: object}>}
 */
export async function registerUser(name, email, password, role = "researcher") {
  const response = await fetch(`${API_BASE_URL}/api/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, email, password, role }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(errorData?.detail || `Registration failed (Status ${response.status})`);
  }

  return await response.json();
}

/**
 * Retrieve profile of currently authenticated user.
 * @returns {Promise<{user: object, disclaimer: string}>}
 */
export async function getCurrentUserProfile() {
  const response = await authFetch(`${API_BASE_URL}/api/auth/me`, {
    method: "GET",
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(errorData?.detail || `Failed to fetch user profile (Status ${response.status})`);
  }

  return await response.json();
}

/**
 * Update display name or password for current user.
 * @param {object} payload - { name, current_password, new_password }
 * @returns {Promise<{message: string, user: object}>}
 */
export async function updateUserProfile(payload) {
  const response = await authFetch(`${API_BASE_URL}/api/auth/profile`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(errorData?.detail || `Failed to update profile (Status ${response.status})`);
  }

  return await response.json();
}

/**
 * Logout user: calls server logout and removes local token.
 * @returns {Promise<{message: string}>}
 */
export async function logoutUser() {
  try {
    await authFetch(`${API_BASE_URL}/api/auth/logout`, { method: "POST" });
  } catch (_) {
    // Ignore server error on logout
  } finally {
    setStoredAuthToken(null);
  }
  return { message: "Logged out successfully" };
}

/**
 * List all users (Admin only).
 * @returns {Promise<{total_users: number, users: Array<object>}>}
 */
export async function getAllUsers() {
  const response = await authFetch(`${API_BASE_URL}/api/auth/users`, {
    method: "GET",
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(errorData?.detail || `Failed to list users (Status ${response.status})`);
  }

  return await response.json();
}

/**
 * Update user role (Admin only).
 * @param {string} userId
 * @param {string} role
 * @returns {Promise<{message: string, user: object}>}
 */
export async function updateUserRole(userId, role) {
  const response = await authFetch(`${API_BASE_URL}/api/auth/users/${encodeURIComponent(userId)}/role`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ role }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(errorData?.detail || `Failed to update role (Status ${response.status})`);
  }

  return await response.json();
}

/**
 * Activate or deactivate user account (Admin only).
 * @param {string} userId
 * @param {boolean} isActive
 * @returns {Promise<{message: string, user: object}>}
 */
export async function updateUserStatus(userId, isActive) {
  const response = await authFetch(`${API_BASE_URL}/api/auth/users/${encodeURIComponent(userId)}/status`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ is_active: isActive }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(errorData?.detail || `Failed to update status (Status ${response.status})`);
  }

  return await response.json();
}

/**
 * Trigger dev-seed endpoint (development mode only).
 * @returns {Promise<{message: string, accounts: Array<object>}>}
 */
export async function devSeedAccounts() {
  const response = await fetch(`${API_BASE_URL}/api/auth/dev-seed`, {
    method: "POST",
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(errorData?.detail || `Dev seed failed (Status ${response.status})`);
  }

  return await response.json();
}

/**
 * Generate a Comprehensive Research Report for a study (Step 11.18).
 * @param {string} studyId
 * @returns {Promise<object>}
 */
export async function generateComprehensiveResearchReport(studyId) {
  const response = await authFetch(
    `${API_BASE_URL}/api/reports/research/${encodeURIComponent(studyId)}`,
    { method: "POST" }
  );

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(
      errorData?.detail || `Failed to generate comprehensive research report (Status ${response.status})`
    );
  }

  return await response.json();
}

/**
 * Generate a ZIP Research Export Package for a study (Step 11.18).
 * @param {string} studyId
 * @returns {Promise<object>}
 */
export async function createResearchExportPackage(studyId) {
  const response = await authFetch(
    `${API_BASE_URL}/api/reports/research/${encodeURIComponent(studyId)}/package`,
    { method: "POST" }
  );

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(
      errorData?.detail || `Failed to export research package (Status ${response.status})`
    );
  }

  return await response.json();
}

/**
 * Retrieve report history for a specific study.
 * @param {string} studyId
 * @returns {Promise<object>}
 */
export async function getStudyReportsHistory(studyId) {
  const response = await authFetch(
    `${API_BASE_URL}/api/reports/history/${encodeURIComponent(studyId)}`,
    { method: "GET" }
  );

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(
      errorData?.detail || `Failed to fetch report history (Status ${response.status})`
    );
  }

  return await response.json();
}

/**
 * Retrieve all reports history accessible to the user.
 * @returns {Promise<object>}
 */
export async function getAllReportsHistory() {
  const response = await authFetch(`${API_BASE_URL}/api/reports/history`, {
    method: "GET",
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(
      errorData?.detail || `Failed to fetch all reports history (Status ${response.status})`
    );
  }

  return await response.json();
}

/**
 * Health check endpoint for system status, version, and environment.
 * @returns {Promise<{status: string, service: string, version: string, environment: string}>}
 */
export async function checkHealth() {
  const response = await fetch(`${API_BASE_URL}/health`);
  if (!response.ok) {
    throw new Error(`Health check failed with status ${response.status}`);
  }
  return await response.json();
}

/**
 * Retrieve system scientific non-clinical disclaimer.
 * @returns {Promise<{disclaimer: string, version: string}>}
 */
export async function getSystemDisclaimer() {
  const response = await fetch(`${API_BASE_URL}/disclaimer`);
  if (!response.ok) {
    throw new Error(`Failed to load system disclaimer with status ${response.status}`);
  }
  return await response.json();
}

/**
 * Helper to extract user-friendly error message from failed HTTP response.
 * @param {Response} response
 * @returns {Promise<string>}
 */
export async function parseErrorResponse(response) {
  try {
    const errorData = await response.json();
    if (errorData?.detail) {
      if (typeof errorData.detail === "string") {
        return errorData.detail;
      } else if (Array.isArray(errorData.detail)) {
        return errorData.detail.map(e => `${e.loc?.slice(1)?.join('.') || 'field'}: ${e.msg}`).join("; ");
      }
    }
    return `Request failed with status ${response.status} (${response.statusText || 'Error'})`;
  } catch {
    if (response.status === 413) {
      return "The uploaded file exceeds the maximum allowed upload size limit.";
    } else if (response.status === 404) {
      return "The requested scientific resource or analysis was not found.";
    } else if (response.status === 403) {
      return "Access denied: You do not have permission to perform this action.";
    } else if (response.status === 401) {
      return "Session expired or authentication required. Please log in.";
    }
    return `Server error with status code ${response.status}`;
  }
}
