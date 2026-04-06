import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { LayoutDashboard, PlusCircle, List, History, PlaySquare, Settings, LogOut, FileAudio } from 'lucide-react';
import { useAuth } from '../auth/AuthContext';

export const Navigation: React.FC<{
  isMobile: boolean;
  onCloseMobile?: () => void;
}> = ({ isMobile, onCloseMobile }) => {
  const { user, logout } = useAuth();
  const location = useLocation();

  const navItems = [
    { path: '/', label: '總覽', icon: LayoutDashboard, exact: true },
    { path: '/submit', label: '提交任務', icon: PlusCircle },
    { path: '/track', label: '任務追蹤', icon: List },
    { path: '/history', label: '歷史記錄', icon: History },
    { path: '/playlists', label: '播放清單', icon: PlaySquare },
    { path: '/settings', label: '設定', icon: Settings },
  ];

  const handleLogout = () => {
    logout();
  };

  // Bottom Tab Bar for Mobile
  if (isMobile) {
    return (
      <nav className="fixed bottom-0 w-full bg-white dark:bg-[#161b22] border-t border-gray-200 dark:border-gray-800 flex flex-row justify-around items-center h-16 z-50 px-2 pb-safe">
        {navItems.map((item) => {
          const isActive = item.exact
            ? location.pathname === item.path
            : location.pathname.startsWith(item.path);

          const Icon = item.icon;

          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={`flex flex-col items-center justify-center w-full h-full space-y-1 ${
                isActive
                  ? 'text-blue-600 dark:text-blue-500'
                  : 'text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
              }`}
            >
              <Icon className="w-5 h-5" />
              <span className="text-[10px] font-medium leading-none">{item.label}</span>
            </NavLink>
          );
        })}
      </nav>
    );
  }

  // Left Sidebar for Desktop
  return (
    <>
      <div className="h-16 flex items-center px-6 border-b border-gray-200 dark:border-gray-800 justify-between shrink-0">
        <div className="flex items-center gap-2 text-blue-600 dark:text-blue-500">
          <FileAudio className="w-6 h-6" />
          <span className="text-xl font-bold">FaYin</span>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto py-4 px-3 space-y-1">
        {navItems.map((item) => {
          const isActive = item.exact
            ? location.pathname === item.path
            : location.pathname.startsWith(item.path);

          const Icon = item.icon;

          return (
            <NavLink
              key={item.path}
              to={item.path}
              onClick={onCloseMobile}
              className={`flex items-center gap-3 px-3 py-2.5 text-sm font-medium rounded-lg transition-colors ${
                isActive
                  ? 'bg-blue-50 text-blue-600 dark:bg-blue-900/20 dark:text-blue-400'
                  : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800/50'
              }`}
            >
              <Icon className="w-5 h-5 flex-shrink-0" />
              {item.label}
            </NavLink>
          );
        })}
      </div>

      <div className="p-4 border-t border-gray-200 dark:border-gray-800 shrink-0">
        <div className="flex items-center px-2 py-2 mb-2">
          <div className="w-8 h-8 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center text-blue-600 dark:text-blue-400 font-medium text-sm mr-3">
            {user?.email?.charAt(0).toUpperCase() || 'U'}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
              {user?.email || 'User'}
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
              {user?.role === 'admin' ? '管理員' : '一般用戶'}
            </p>
          </div>
        </div>
        <button
          onClick={handleLogout}
          className="w-full flex items-center gap-3 px-3 py-2 text-sm font-medium rounded-lg text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
        >
          <LogOut className="w-5 h-5 flex-shrink-0" />
          登出
        </button>
      </div>
    </>
  );
};

export default Navigation;