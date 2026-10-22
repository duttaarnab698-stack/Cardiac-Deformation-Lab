import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { AnalysisProvider } from "./context/AnalysisContext";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import Studies from "./pages/Studies";
import StudyDetail from "./pages/StudyDetail";
import Analysis from "./pages/Analysis";
import TemporalAnalysisPage from "./pages/TemporalAnalysisPage";
import Results from "./pages/Results";
import Comparison from "./pages/Comparison";
import LongitudinalAnalysis from "./pages/LongitudinalAnalysis";
import Statistics from "./pages/Statistics";
import SyntheticValidation from "./pages/SyntheticValidation";
import AnnotationWorkbench from "./pages/AnnotationWorkbench";
import RealValidation from "./pages/RealValidation";
import AnalysisExplorer from "./pages/AnalysisExplorer";
import ResearchReports from "./pages/ResearchReports";
import Settings from "./pages/Settings";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Profile from "./pages/Profile";
import AdminUsers from "./pages/AdminUsers";
import "./App.css";

function ProtectedRoute({ children }) {
  const { isAuthenticated, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="auth-loading-screen">
        <div className="auth-loading-spinner" />
        <p>Loading research workspace...</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return children;
}

function AdminRoute({ children }) {
  const { isAuthenticated, isAdmin, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="auth-loading-screen">
        <div className="auth-loading-spinner" />
        <p>Verifying administrative privileges...</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (!isAdmin) {
    return <Navigate to="/" replace />;
  }

  return children;
}

export default function App() {
  return (
    <AuthProvider>
      <AnalysisProvider>
        <BrowserRouter>
          <Routes>
            {/* Public Auth Routes */}
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />

            {/* Protected Workspace Routes */}
            <Route
              path="/"
              element={
                <ProtectedRoute>
                  <Layout />
                </ProtectedRoute>
              }
            >
              <Route index element={<Dashboard />} />
              <Route path="dashboard" element={<Dashboard />} />
              <Route path="studies" element={<Studies />} />
              <Route path="studies/:studyId" element={<StudyDetail />} />
              <Route path="longitudinal" element={<LongitudinalAnalysis />} />
              <Route path="longitudinal/:studyId" element={<LongitudinalAnalysis />} />
              <Route path="statistics" element={<Statistics />} />
              <Route path="statistics/:studyId" element={<Statistics />} />
              <Route path="synthetic-validation" element={<SyntheticValidation />} />
              <Route path="annotations" element={<AnnotationWorkbench />} />
              <Route path="annotations/:analysisId" element={<AnnotationWorkbench />} />
              <Route path="real-validation" element={<RealValidation />} />
              <Route path="real-validation/:analysisId" element={<RealValidation />} />
              <Route path="analysis" element={<Analysis />} />
              <Route path="temporal" element={<TemporalAnalysisPage />} />
              <Route path="results" element={<Results />} />
              <Route path="explorer" element={<AnalysisExplorer />} />
              <Route path="explorer/:analysisId" element={<AnalysisExplorer />} />
              <Route path="comparison" element={<Comparison />} />
              <Route path="reports" element={<ResearchReports />} />
              <Route path="profile" element={<Profile />} />
              <Route
                path="admin/users"
                element={
                  <AdminRoute>
                    <AdminUsers />
                  </AdminRoute>
                }
              />
              <Route path="settings" element={<Settings />} />
            </Route>

            {/* Fallback */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </AnalysisProvider>
    </AuthProvider>
  );
}
