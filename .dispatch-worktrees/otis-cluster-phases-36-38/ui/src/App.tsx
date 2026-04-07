import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { WorkspaceUI } from './components/WorkspaceUI';
import { ProjectView } from './pages/ProjectView';
import './App.css';

function App() {
  return (
    <Router>
      <div className="App">
        <Routes>
          <Route path="/" element={<WorkspaceUI />} />
          <Route path="/project/:projectName" element={<ProjectView />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
