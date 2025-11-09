
import React, { useEffect } from 'react';
import { HashRouter, Routes, Route, useLocation } from 'react-router-dom';
import DashboardPage from './pages/DashboardPage';
import AreaDetailsPage from './pages/AreaDetailsPage';

// Component to scroll to top on route change
function ScrollToTop() {
  const { pathname } = useLocation();

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);

  return null;
}

const App: React.FC = () => {
  return (
    <HashRouter>
      <ScrollToTop />
      <div className="min-h-screen bg-gray-50">
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/areas/:areaId" element={<AreaDetailsPage />} />
        </Routes>
      </div>
    </HashRouter>
  );
};

export default App;
