import React, { useState, useEffect } from 'react';
import { Settings as SettingsIcon, Mail, Save, LogOut, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';
import { useAuth } from '../auth/AuthContext';
import api from '../api/client';

export default function Settings() {
  const { user, logout } = useAuth();
  const [notificationEmail, setNotificationEmail] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);

  useEffect(() => {
    // Fetch current settings if needed, or use user email as default
    if (user?.email) {
      setNotificationEmail(user.email);
    }
  }, [user]);

  const handleSaveSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    setMessage(null);

    try {
      // POST to user preferences endpoint or /api/config
      await api.post('/config', {
        notification_email: notificationEmail,
      });
      setMessage({ type: 'success', text: '設定已儲存' });
    } catch (err: any) {
      setMessage({ type: 'error', text: err.response?.data?.detail || '儲存失敗' });
    } finally {
      setIsSaving(false);
    }
  };

  const handleLogout = () => {
    if (window.confirm('確定要登出嗎？')) {
      logout();
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6 pb-20">
      <div>
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white flex items-center gap-2">
          <SettingsIcon className="w-5 h-5 text-blue-500" />
          個人設定
        </h2>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">管理您的通知偏好與帳號設定</p>
      </div>

      {/* Notification Settings */}
      <div className="bg-white dark:bg-[#161b22] rounded-2xl border border-gray-200 dark:border-gray-800 shadow-sm overflow-hidden">
        <div className="p-6 border-b border-gray-200 dark:border-gray-800">
          <h3 className="text-md font-medium text-gray-900 dark:text-white">通知設定</h3>
        </div>
        <form onSubmit={handleSaveSettings} className="p-6 space-y-6">
          <div className="space-y-2">
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300 flex items-center gap-2">
              <Mail className="w-4 h-4 text-gray-400" />
              通知電子信箱
            </label>
            <input
              type="email"
              placeholder="your-email@example.com"
              className="w-full px-4 py-2.5 bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all dark:text-white"
              value={notificationEmail}
              onChange={(e) => setNotificationEmail(e.target.value)}
              required
            />
            <p className="text-xs text-gray-500 dark:text-gray-400">
              任務完成或發生錯誤時，系統會發送通知至此信箱。
            </p>
          </div>

          {message && (
            <div className={`p-3 rounded-lg flex items-center gap-2 text-sm ${
              message.type === 'success' ? 'bg-green-50 text-green-700 dark:bg-green-500/10 dark:text-green-400' : 'bg-red-50 text-red-700 dark:bg-red-500/10 dark:text-red-400'
            }`}>
              {message.type === 'success' ? <CheckCircle2 className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}
              {message.text}
            </div>
          )}

          <div className="flex justify-end pt-2">
            <button
              type="submit"
              disabled={isSaving}
              className="px-6 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white font-medium rounded-xl transition-colors flex items-center justify-center gap-2 shadow-sm"
            >
              {isSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
              儲存設定
            </button>
          </div>
        </form>
      </div>

      {/* Account Info & Logout */}
      <div className="bg-white dark:bg-[#161b22] rounded-2xl border border-gray-200 dark:border-gray-800 shadow-sm overflow-hidden">
        <div className="p-6 border-b border-gray-200 dark:border-gray-800">
          <h3 className="text-md font-medium text-gray-900 dark:text-white">帳號資訊</h3>
        </div>
        <div className="p-6 space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-900 dark:text-white">{user?.email}</p>
              <p className="text-xs text-gray-500 dark:text-gray-400 capitalize">{user?.role || 'User'}</p>
            </div>
            <button
              onClick={handleLogout}
              className="flex items-center gap-2 px-4 py-2 text-red-600 hover:bg-red-50 dark:hover:bg-red-500/10 rounded-xl transition-colors font-medium border border-red-200 dark:border-red-900/30"
            >
              <LogOut className="w-4 h-4" />
              登出
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
