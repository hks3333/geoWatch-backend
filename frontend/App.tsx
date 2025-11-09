
import React from 'react';
import { HashRouter, Routes, Route } from 'react-router-dom';
import DashboardPage from './pages/DashboardPage';
import AreaDetailsPage from './pages/AreaDetailsPage';

const App: React.FC = () => {
  return (
    <HashRouter>
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
