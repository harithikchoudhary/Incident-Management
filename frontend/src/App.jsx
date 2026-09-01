import { useEffect, useState } from "react";
import { Routes, Route } from "react-router-dom";
import { Menu } from "lucide-react";
import Sidebar from "./components/Sidebar.jsx";
import ChatPage from "./pages/ChatPage.jsx";
import DashboardPage from "./pages/DashboardPage.jsx";
import HistoricalPage from "./pages/HistoricalPage.jsx";
import SearchPage from "./pages/SearchPage.jsx";
import IngestionPage from "./pages/IngestionPage.jsx";
import { api } from "./api/client.js";

export default function App() {
  const [health, setHealth] = useState("checking");
  const [sidebarOpen, setSidebarOpen] = useState(false);

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
    <div className="flex h-screen overflow-hidden bg-ink-50">
      <Sidebar health={health} open={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        {/* Mobile top bar */}
        <div className="flex items-center gap-3 border-b border-ink-100 bg-white px-4 py-3 shadow-sm lg:hidden">
          <button
            className="rounded-lg p-1.5 text-ink-600 hover:bg-ink-50"
            onClick={() => setSidebarOpen(true)}
            aria-label="Open menu"
          >
            <Menu className="h-6 w-6" />
          </button>
          <img
            src="/download.jpg"
            alt="L&T Finance"
            className="h-7 w-auto max-w-[140px] rounded-md object-contain"
            onError={(e) => {
              e.currentTarget.style.display = "none";
              e.currentTarget.nextSibling.style.display = "inline";
            }}
          />
          <span className="hidden text-sm font-bold text-ink-800">L&amp;T Finance</span>
        </div>

        <main className="min-w-0 flex-1 overflow-y-auto">
          <Routes>
            <Route path="/" element={<ChatPage />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/incidents" element={<HistoricalPage />} />
            <Route path="/search" element={<SearchPage />} />
            <Route path="/ingestion" element={<IngestionPage />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}
