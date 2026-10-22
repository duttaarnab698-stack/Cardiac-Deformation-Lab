import { useState } from "react";
import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";
import Header from "./Header";
import "./Navigation.css";

export default function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const toggleSidebar = () => {
    setSidebarOpen((prev) => !prev);
  };

  const closeSidebar = () => {
    setSidebarOpen(false);
  };

  return (
    <div className="dashboard-app-layout">
      <Sidebar isOpen={sidebarOpen} onClose={closeSidebar} />

      <div className="dashboard-main-wrapper">
        <Header onToggleSidebar={toggleSidebar} />

        <main className="dashboard-main-content">
          <Outlet />
        </main>

        <footer className="dashboard-footer">
          <p>
            Cardiac Deformation Lab v1.0.4 &bull; Computational Biomechanical Motion &amp; Strain Analysis &bull; Research Prototype — Not For Diagnostic Use
          </p>
        </footer>
      </div>
    </div>
  );
}

