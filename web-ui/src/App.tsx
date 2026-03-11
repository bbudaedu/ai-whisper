import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { Play, Settings, TerminalSquare, LayoutDashboard, Database, HardDrive, RefreshCcw, SlidersHorizontal, ListChecks } from 'lucide-react';
import LogViewer from './components/LogViewer';
import TaskTracker from './components/TaskTracker';
import SettingsPanel from './components/SettingsPanel';
import PlaylistDashboard from './components/PlaylistDashboard';
import PlaylistTaskManager from './components/PlaylistTaskManager';
import { DashboardData, EpisodeRecord } from './types';

const API_BASE = `http://${window.location.hostname}:8002/api`;

function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [stats, setStats] = useState<Record<string, EpisodeRecord>>({});
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);

  const fetchStatus = useCallback(async () => {
    try {
      const res = await axios.get(`${API_BASE}/status`);
      setStats(res.data);
    } catch (e) {
      console.error('Failed to fetch status', e);
    }
  }, []);

  const fetchDashboard = useCallback(async () => {
    try {
      const res = await axios.get(`${API_BASE}/dashboard`);
      setDashboardData(res.data);
    } catch (e) {
      console.error('Failed to fetch dashboard', e);
    }
  }, []);

  useEffect(() => {
    // Use setTimeout to avoid synchronous setState trigger warning in some lint rules
    const timer = setTimeout(() => {
      void fetchStatus();
      void fetchDashboard();
    }, 0);

    const interval = setInterval(() => {
      void fetchStatus();
      void fetchDashboard();
    }, 10000);
    return () => {
      clearTimeout(timer);
      clearInterval(interval);
    };
  }, [fetchStatus, fetchDashboard]);

  return (
    <div className="flex h-screen w-full bg-[#f9f9fb] dark:bg-[#0f1115] text-slate-800 dark:text-slate-200 font-sans overflow-hidden">
      {/* Sidebar */}
      <aside className="w-64 bg-white dark:bg-[#161b22] border-r border-slate-200 dark:border-slate-800 flex flex-col justify-between hidden md:flex shrink-0">
        <div>
          <div className="p-6 flex items-center space-x-3 border-b border-slate-100 dark:border-slate-800">
            <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center text-white shadow-md shadow-indigo-500/30">
              <Database size={18} />
            </div>
            <span className="font-bold text-lg tracking-tight">AI Whisper</span>
          </div>
          <nav className="p-4 space-y-1">
            <button
              onClick={() => setActiveTab('dashboard')}
              className={`w-full flex items-center space-x-3 px-4 py-3 rounded-xl transition-all ${activeTab === 'dashboard' ? 'bg-indigo-50 dark:bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 font-medium' : 'hover:bg-slate-50 dark:hover:bg-slate-800 border border-transparent'}`}
            >
              <LayoutDashboard size={18} />
              <span>儀表板 (Dashboard)</span>
            </button>
            <button
              onClick={() => setActiveTab('tasks')}
              className={`w-full flex items-center space-x-3 px-4 py-3 rounded-xl transition-all ${activeTab === 'tasks' ? 'bg-indigo-50 dark:bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 font-medium' : 'hover:bg-slate-50 dark:hover:bg-slate-800 border border-transparent'}`}
            >
              <ListChecks size={18} />
              <span>任務管理 (Tasks)</span>
            </button>
            <button
              onClick={() => setActiveTab('logs')}
              className={`w-full flex items-center space-x-3 px-4 py-3 rounded-xl transition-all ${activeTab === 'logs' ? 'bg-indigo-50 dark:bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 font-medium' : 'hover:bg-slate-50 dark:hover:bg-slate-800 border border-transparent'}`}
            >
              <TerminalSquare size={18} />
              <span>即時日誌 (Logs)</span>
            </button>
            <button
              onClick={() => setActiveTab('settings')}
              className={`w-full flex items-center space-x-3 px-4 py-3 rounded-xl transition-all ${activeTab === 'settings' ? 'bg-indigo-50 dark:bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 font-medium' : 'hover:bg-slate-50 dark:hover:bg-slate-800 border border-transparent'}`}
            >
              <SlidersHorizontal size={18} />
              <span>系統設定 (Settings)</span>
            </button>
          </nav>
        </div>
        <div className="p-4 border-t border-slate-200 dark:border-slate-800">
          <div className="flex items-center space-x-3 text-sm text-slate-500 dark:text-slate-400 px-4 py-2">
            <HardDrive size={16} />
            <span>服務執行中 (Server Active)</span>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col h-screen overflow-hidden">
        {/* Header */}
        <header className="h-16 bg-white dark:bg-[#161b22] border-b border-slate-200 dark:border-slate-800 px-8 flex items-center justify-between shrink-0">
          <h1 className="text-xl font-semibold">
            {activeTab === 'dashboard' ? '任務與狀態總覽' :
              activeTab === 'tasks' ? '播放清單任務管理' :
                activeTab === 'logs' ? '系統即時日誌' : '全局參數設定'}
          </h1>
          <div className="flex items-center space-x-4">
            <button onClick={fetchStatus} className="p-2 rounded-full hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors text-slate-500">
              <RefreshCcw size={18} />
            </button>
            <div className="w-8 h-8 rounded-full bg-slate-200 dark:bg-slate-700"></div>
          </div>
        </header>

        {/* Scrollable Area */}
        <div className="flex-1 overflow-y-auto min-h-screen bg-slate-50 dark:bg-[#0d1117] text-slate-900 dark:text-slate-200 font-sans transition-colors">
          {activeTab === 'dashboard' && (
            <div className="w-full px-4 mx-auto space-y-6 py-4 md:py-8">
              {/* Action Buttons */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <button
                  onClick={() => axios.post(`${API_BASE}/task`, { action: 'proofread', target: 'auto' })}
                  className="bg-[#3B82F6] hover:bg-[#2563EB] text-white rounded-xl px-5 py-3.5 font-medium flex items-center justify-center space-x-2 transition-colors focus:ring-4 focus:ring-blue-500/20 cursor-pointer"
                >
                  <Play size={18} />
                  <span>一鍵啟動自動校對</span>
                </button>
                <button
                  onClick={() => axios.post(`${API_BASE}/task`, { action: 'whisper', target: 'auto' })}
                  className="bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 rounded-xl px-5 py-3.5 font-medium flex items-center justify-center space-x-2 transition-colors cursor-pointer"
                >
                  <Settings size={18} />
                  <span>執行 Whisper 轉錄</span>
                </button>
              </div>

              {/* Multi-Playlist Dashboard */}
              <PlaylistDashboard data={dashboardData} />

              {/* Legacy Task Tracker */}
              <div className="bg-white dark:bg-[#1c2128] rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden">
                <div className="p-6 border-b border-slate-100 dark:border-slate-800 flex justify-between items-center">
                  <h2 className="text-lg font-semibold">全部影片追蹤 (All Videos)</h2>
                </div>
                <TaskTracker stats={stats} />
              </div>
            </div>
          )}

          {activeTab === 'tasks' && (
            <div className="w-full px-4 mx-auto py-4 md:py-8">
              <PlaylistTaskManager data={dashboardData} onRefresh={fetchDashboard} />
            </div>
          )}

          {activeTab === 'logs' && (
            <div className="w-full px-4 mx-auto h-[calc(100vh-10rem)] py-4 md:py-8">
              <LogViewer />
            </div>
          )}

          {activeTab === 'settings' && (
            <div className="w-full px-4 mx-auto py-4 md:py-8">
              <SettingsPanel />
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

export default App;
