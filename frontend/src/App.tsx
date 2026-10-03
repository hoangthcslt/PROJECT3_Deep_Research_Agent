import { BrowserRouter, Routes, Route } from "react-router-dom";
import ResearchInput from "./pages/ResearchInput";
import ResearchProgress from "./pages/ResearchProgress";
import ReportView from "./pages/ReportView";
import KnowledgeGraph from "./pages/KnowledgeGraph";
import "./App.css";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<ResearchInput />} />
        <Route path="/research/:sessionId" element={<ResearchProgress />} />
        <Route path="/report/:sessionId" element={<ReportView />} />
        <Route path="/graph/:sessionId" element={<KnowledgeGraph />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
