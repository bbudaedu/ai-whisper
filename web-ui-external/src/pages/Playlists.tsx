import React, { useState } from 'react';
import { Youtube, Plus, Trash2, Power, PowerOff, LayoutList, Loader2, AlertCircle, CheckCircle2 } from 'lucide-react';
import api from '../api/client';
import { usePolling } from '../hooks/usePolling';

interface PlaylistStats {
  whispered: number;
  proofread: number;
  pending: number;
}

interface Playlist {
  id: string;
  name: string;
  url: string;
  enabled: boolean;
  total_videos: number;
  stats: PlaylistStats;
  status: 'idle' | 'running' | 'paused' | 'error';
}

export default function Playlists() {
  const [newUrl, setNewUrl] = useState('');
  const [isAdding, setIsAdding] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState<string | null>(null);

  const { data: playlists, loading, error, manualRefresh } = usePolling<Playlist[]>('/playlists', 10000);

  const handleAddPlaylist = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newUrl) return;

    setIsAdding(true);
    setMessage(null);
    try {
      await api.post('/playlists', { url: newUrl });
      setNewUrl('');
      setMessage({ type: 'success', text: '成功新增播放清單' });
      manualRefresh();
    } catch (err: any) {
      setMessage({ type: 'error', text: err.response?.data?.detail || '新增失敗' });
    } finally {
      setIsAdding(false);
    }
  };

  const handleToggleTracking = async (id: string, currentStatus: boolean) => {
    try {
      await api.put(`/playlists/${id}/control`, { enabled: !currentStatus });
      manualRefresh();
    } catch (err) {
      console.error('Toggle failed', err);
    }
  };

  const handleDeletePlaylist = async (id: string) => {
    try {
      await api.delete(`/playlists/${id}`);
      setShowDeleteConfirm(null);
      manualRefresh();
    } catch (err) {
      console.error('Delete failed', err);
    }
  };

  return (
    <div className="space-y-6 pb-20">
      <div>
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white">播放清單管理</h2>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">追蹤 YouTube 播放清單，自動將新影片加入轉錄佇列</p>
      </div>

      {/* Add Playlist Form */}
      <div className="bg-white dark:bg-[#161b22] p-6 rounded-2xl border border-gray-200 dark:border-gray-800 shadow-sm">
        <form onSubmit={handleAddPlaylist} className="flex flex-col sm:flex-row gap-3">
          <div className="flex-1 relative">
            <Youtube className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="url"
              placeholder="輸入 YouTube 播放清單網址..."
              className="w-full pl-10 pr-4 py-2.5 bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all dark:text-white"
              value={newUrl}
              onChange={(e) => setNewUrl(e.target.value)}
              required
            />
          </div>
          <button
            type="submit"
            disabled={isAdding || !newUrl}
            className="px-6 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white font-medium rounded-xl transition-colors flex items-center justify-center gap-2"
          >
            {isAdding ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
            新增追蹤
          </button>
        </form>

        {message && (
          <div className={`mt-4 p-3 rounded-lg flex items-center gap-2 text-sm ${
            message.type === 'success' ? 'bg-green-50 text-green-700 dark:bg-green-500/10 dark:text-green-400' : 'bg-red-50 text-red-700 dark:bg-red-500/10 dark:text-red-400'
          }`}>
            {message.type === 'success' ? <CheckCircle2 className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}
            {message.text}
          </div>
        )}
      </div>

      {/* Playlists List */}
      {loading && !playlists ? (
        <div className="flex justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
        </div>
      ) : error ? (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-4 text-red-700 dark:text-red-400 text-sm">
          無法載入播放清單：{error.message}
        </div>
      ) : playlists?.length === 0 ? (
        <div className="bg-white dark:bg-[#161b22] border border-gray-200 dark:border-gray-800 rounded-xl p-12 text-center">
          <LayoutList className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">尚無追蹤的播放清單</h3>
          <p className="text-sm text-gray-500 dark:text-gray-400">新增播放清單網址以開始自動化處理流程。</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {playlists?.map((pl) => (
            <div key={pl.id} className="bg-white dark:bg-[#161b22] p-5 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm flex flex-col h-full">
              <div className="flex justify-between items-start mb-4">
                <div className="flex-1 min-w-0">
                  <h3 className="font-bold text-gray-900 dark:text-white truncate" title={pl.name}>{pl.name}</h3>
                  <p className="text-xs text-gray-400 font-mono truncate">{pl.id}</p>
                </div>
                <div className="flex items-center gap-1 ml-2">
                  <button
                    onClick={() => handleToggleTracking(pl.id, pl.enabled)}
                    title={pl.enabled ? "暫停追蹤" : "啟用追蹤"}
                    className={`p-2 rounded-lg transition-colors ${
                      pl.enabled
                        ? 'text-emerald-600 bg-emerald-50 hover:bg-emerald-100 dark:bg-emerald-500/10 dark:text-emerald-400'
                        : 'text-gray-400 bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-500'
                    }`}
                  >
                    {pl.enabled ? <Power className="w-4 h-4" /> : <PowerOff className="w-4 h-4" />}
                  </button>
                  <button
                    onClick={() => setShowDeleteConfirm(pl.id)}
                    className="p-2 text-red-600 bg-red-50 hover:bg-red-100 dark:bg-red-500/10 dark:text-red-400 rounded-lg transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-2 mb-4">
                <div className="bg-gray-50 dark:bg-gray-800/50 p-2 rounded-lg text-center">
                  <div className="text-xs text-gray-500 dark:text-gray-400">總影片</div>
                  <div className="font-bold text-gray-900 dark:text-white">{pl.total_videos}</div>
                </div>
                <div className="bg-gray-50 dark:bg-gray-800/50 p-2 rounded-lg text-center">
                  <div className="text-xs text-gray-500 dark:text-gray-400">已轉錄</div>
                  <div className="font-bold text-emerald-600 dark:text-emerald-400">{pl.stats.whispered}</div>
                </div>
                <div className="bg-gray-50 dark:bg-gray-800/50 p-2 rounded-lg text-center">
                  <div className="text-xs text-gray-500 dark:text-gray-400">待處理</div>
                  <div className="font-bold text-amber-600 dark:text-amber-400">{pl.stats.pending}</div>
                </div>
              </div>

              <div className="mt-auto flex justify-between items-center text-xs">
                <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full ${
                  pl.status === 'running' ? 'text-emerald-600 bg-emerald-50 dark:bg-emerald-500/10' : 'text-gray-500 bg-gray-100 dark:bg-gray-800'
                }`}>
                  <span className={`w-1.5 h-1.5 rounded-full ${pl.status === 'running' ? 'bg-emerald-500 animate-pulse' : 'bg-gray-400'}`} />
                  {pl.status === 'running' ? '執行中' : '閒置'}
                </span>
                <a
                  href={pl.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-1"
                >
                  <Youtube className="w-3 h-3" />
                  查看網址
                </a>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
          <div className="bg-white dark:bg-[#161b22] rounded-2xl border border-gray-200 dark:border-gray-800 p-6 max-w-sm w-full shadow-2xl">
            <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-2">刪除播放清單</h3>
            <p className="text-gray-500 dark:text-gray-400 text-sm mb-6">
              確定要停止追蹤並刪除此播放清單嗎？這不會刪除已產生的轉錄結果。
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setShowDeleteConfirm(null)}
                className="flex-1 px-4 py-2 bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 rounded-xl font-medium"
              >
                取消
              </button>
              <button
                onClick={() => handleDeletePlaylist(showDeleteConfirm)}
                className="flex-1 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-xl font-medium"
              >
                確認刪除
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
