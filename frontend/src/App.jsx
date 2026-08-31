import { useEffect, useState } from "react";
import { Routes, Route } from "react-router-dom";
import Sidebar from "./components/Sidebar.jsx";
import ChatPage from "./pages/ChatPage.jsx";
import DashboardPage from "./pages/DashboardPage.jsx";
import HistoricalPage from "./pages/HistoricalPage.jsx";
import SearchPage from "./pages/SearchPage.jsx";
import IngestionPage from "./pages/IngestionPage.jsx";
import { api } from "./api/client.js";

export default function App() {
  const [health, setHealth] = useState("checking");

  useEffect(() => {
    let active = true;
    const check = async () => {
      try {
        await api.health();
        if (active) setHealth("connected");
      } catch {
        if (active) setHealth("disconnected");
      }
    };
    check();
    const interval = setInterval(check, 15000);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, []);

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar health={health} />
      <main className="flex-1 overflow-y-auto">
        <Routes>
          <Route path="/" element={<ChatPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/incidents" element={<HistoricalPage />} />
          <Route path="/search" element={<SearchPage />} />
          <Route path="/ingestion" element={<IngestionPage />} />
        </Routes>
      </main>
    </div>
  );
}
