import { useState, useEffect } from 'react'
import { Menu, X } from 'lucide-react'
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { AuthProvider } from './auth/AuthContext'
import { ProtectedRoute } from './components/ProtectedRoute'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import SubmitTask from './pages/SubmitTask'
import TaskTracker from './pages/TaskTracker'
import Playlists from './pages/Playlists'
import Navigation from './components/Navigation'

// Title updater component
function PageTitle() {
  const location = useLocation();
  const [title, setTitle] = useState('總覽');

  useEffect(() => {
    switch (location.pathname) {
      case '/':
        setTitle('總覽');
        break;
      case '/submit':
        setTitle('提交任務');
        break;
      case '/track':
        setTitle('任務追蹤');
        break;
      case '/playlists':
        setTitle('播放清單');
        break;
      case '/settings':
        setTitle('設定');
        break;
      default:
        setTitle('FaYin');
    }
  }, [location]);

  return <h1 className="text-lg font-semibold text-gray-900 dark:text-white">{title}</h1>;
}

function AppLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)

  const toggleSidebar = () => setSidebarOpen(!sidebarOpen)
  const closeSidebar = () => setSidebarOpen(false)

  return (
    <div className="flex w-full min-h-screen pb-16 md:pb-0"> {/* Padding bottom for mobile nav */}
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 md:hidden"
          onClick={closeSidebar}
        />
      )}

      {/* Desktop Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 w-64 transform transition-transform duration-300 ease-in-out md:relative md:translate-x-0 ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        } bg-white dark:bg-[#161b22] border-r border-gray-200 dark:border-gray-800 flex flex-col hidden md:flex`}
      >
        <Navigation isMobile={false} onCloseMobile={closeSidebar} />
      </aside>

      {/* Mobile Sidebar (Slide-out menu for mobile if needed, though bottom nav is primary) */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 w-64 transform transition-transform duration-300 ease-in-out md:hidden ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        } bg-white dark:bg-[#161b22] border-r border-gray-200 dark:border-gray-800 flex flex-col`}
      >
        <div className="h-16 flex items-center px-6 border-b border-gray-200 dark:border-gray-800 justify-between shrink-0">
          <span className="text-xl font-bold text-blue-500">FaYin</span>
          <button className="p-2 -mr-2 text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white" onClick={toggleSidebar}>
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* We can still render the Navigation here for mobile slide-out, but pass isMobile=false to render the list layout */}
        <Navigation isMobile={false} onCloseMobile={closeSidebar} />
      </aside>

      {/* Mobile Bottom Navigation */}
      <div className="md:hidden">
        <Navigation isMobile={true} />
      </div>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col min-w-0 bg-[#f9f9fb] dark:bg-[#0f1115]">
        {/* Header */}
        <header className="h-16 flex items-center px-4 md:px-6 bg-white dark:bg-[#161b22] border-b border-gray-200 dark:border-gray-800 shadow-sm sticky top-0 z-30 shrink-0">
          <button
            className="p-2 -ml-2 mr-4 md:hidden text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white"
            onClick={toggleSidebar}
          >
            <Menu className="w-6 h-6" />
          </button>
          <PageTitle />
        </header>

        {/* Content */}
        <div className="p-4 md:p-6 flex-1 overflow-auto">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            {/* Placeholder routes for now */}
            <Route path="/submit" element={<SubmitTask />} />
            <Route path="/track" element={<TaskTracker />} />
            <Route path="/playlists" element={<Playlists />} />
            <Route path="/settings" element={<div className="p-4 text-gray-500">Settings Page (Coming soon)</div>} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>
      </main>
    </div>
  )
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/*" element={<ProtectedRoute><AppLayout /></ProtectedRoute>} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}

export default App
