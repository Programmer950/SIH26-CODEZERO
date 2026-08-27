import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Sidebar from "./components/Sidebar";
import Dashboard from "./pages/Dashboard";
import Vehicles from "./pages/Vehicles";
import Traffic from "./pages/Traffic";
import Alerts from "./pages/Alerts";

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex min-h-screen bg-[#0f1219] text-slate-200">
        <Sidebar />
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/vehicles" element={<Vehicles />} />
          <Route path="/traffic" element={<Traffic />} />
          <Route path="/alerts" element={<Alerts />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}
