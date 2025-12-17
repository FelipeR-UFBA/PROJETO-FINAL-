
import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { MantineProvider, createTheme } from '@mantine/core';
import { Notifications } from '@mantine/notifications';
import LandingPage from './components/LandingPage';
import Dashboard from './components/Dashboard';
import AnalyticsPanel from './components/AnalyticsPanel';

import '@mantine/core/styles.css';
import '@mantine/notifications/styles.css';

const theme = createTheme({
  primaryColor: 'cyan',
  fontFamily: 'Inter, sans-serif',
});

function App() {
  return (
    <MantineProvider theme={theme} defaultColorScheme="dark">
      <Notifications />
      <Router>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/lab" element={<Dashboard />} />
          <Route path="/analytics" element={<AnalyticsPanel />} />
        </Routes>
      </Router>
    </MantineProvider>
  );
}

export default App;
