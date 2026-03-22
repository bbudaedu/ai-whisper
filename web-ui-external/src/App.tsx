import { useState } from 'react'
import { Menu, X, Home, FileAudio, Settings, LogOut } from 'lucide-react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './auth/AuthContext'
import { ProtectedRoute } from './components/ProtectedRoute'
import Login from './pages/Login'

function AppLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const { logout, user } = useAuth()

  const toggleSidebar = () => setSidebarOpen(!sidebarOpen)

  const handleLogout = () => {
    logout()
  }

  return (
    <div className="flex w-full min-h-screen">
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 w-64 transform transition-transform duration-300 ease-in-out md:relative md:translate-x-0 ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        } bg-white dark:bg-[#161b22] border-r border-gray-200 dark:border-gray-800 flex flex-col`}
      >
        <div className="h-16 flex items-center px-6 border-b border-gray-200 dark:border-gray-800 justify-between">
          <span className="text-xl font-bold text-blue-500">FaYin</span>
          <button className="md:hidden p-2 -mr-2 text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white" onClick={toggleSidebar}>
            <X className="w-5 h-5" />
          </button>
        </div>

        <nav className="flex-1 p-4 space-y-1">
          <a href="#" className="flex items-center gap-3 px-3 py-2 text-sm font-medium rounded-md bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400">
            <Home className="w-5 h-5" />
            總覽
          </a>
          <a href="#" className="flex items-center gap-3 px-3 py-2 text-sm font-medium rounded-md text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800">
            <FileAudio className="w-5 h-5" />
            轉錄任務
          </a>
          <a href="#" className="flex items-center gap-3 px-3 py-2 text-sm font-medium rounded-md text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800">
            <Settings className="w-5 h-5" />
            設定
          </a>
        </nav>

        <div className="p-4 border-t border-gray-200 dark:border-gray-800">
          <div className="flex items-center justify-between px-3 py-2 text-sm text-gray-700 dark:text-gray-300 mb-2">
            <span className="truncate">{user?.email || 'User'}</span>
          </div>
          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-3 px-3 py-2 text-sm font-medium rounded-md text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
          >
            <LogOut className="w-5 h-5" />
            登出
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col min-w-0 bg-[#f9f9fb] dark:bg-[#0f1115]">
        {/* Header */}
        <header className="h-16 flex items-center px-4 md:px-6 bg-white dark:bg-[#161b22] border-b border-gray-200 dark:border-gray-800 shadow-sm sticky top-0 z-30">
          <button
            className="p-2 -ml-2 mr-4 md:hidden text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white"
            onClick={toggleSidebar}
          >
            <Menu className="w-6 h-6" />
          </button>
          <h1 className="text-lg font-semibold text-gray-900 dark:text-white">總覽</h1>
        </header>

        {/* Content */}
        <div className="p-4 md:p-6 flex-1 overflow-auto">
          <div className="max-w-6xl mx-auto">
            {/* Card Example */}
            <div className="bg-white dark:bg-[#161b22] rounded-xl shadow-sm border border-gray-200 dark:border-gray-800 p-6 mb-6">
              <h2 className="text-xl font-bold mb-4 text-gray-900 dark:text-white">歡迎使用 FaYin</h2>
              <p className="text-gray-600 dark:text-gray-400 mb-6">
                這是全新的外部客戶端介面，您可以從這裡上傳音檔進行轉錄，或是設定 YouTube 播放清單自動偵測。
              </p>
              <button className="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white font-medium rounded-lg transition-colors">
                建立新任務
              </button>
            </div>
          </div>
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
          <Route path="/" element={<ProtectedRoute><AppLayout /></ProtectedRoute>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}

export default App
