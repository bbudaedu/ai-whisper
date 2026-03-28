import React, { useState, useMemo } from 'react';
import { FileText, CheckCircle, Clock, XCircle, RefreshCw, Download, ChevronDown, ChevronRight, AlertCircle, FileAudio, Trash2 } from 'lucide-react';
import { usePolling } from '../hooks/usePolling';
import client from '../api/client';

interface TaskRecord {
  id: number;
  url: string;
  status: 'queued' | 'pending' | 'running' | 'downloading' | 'processing' | 'done' | 'failed' | 'canceled';
  title?: string;
  created_at: string;
  updated_at?: string;
  error?: string;
}

export default function TaskTracker() {
  const { data: tasksList, loading, error, manualRefresh } = usePolling<TaskRecord[]>('tasks/history', 10000);
  const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set());
  const [cancellingId, setCancellingId] = useState<number | null>(null);

  const handleCancel = async (taskId: number) => {
    if (!window.confirm('確定要取消這個任務嗎？')) return;

    setCancellingId(taskId);
    try {
      await client.post(`/tasks/${taskId}/cancel`);
      manualRefresh();
    } catch (err: any) {
      alert(`取消失敗: ${err.response?.data?.detail || err.message}`);
    } finally {
      setCancellingId(null);
    }
  };

  const tasks = useMemo(() => {
    if (!tasksList || !Array.isArray(tasksList)) return [];

    // Filter for active tasks OR done tasks (for E2E verification)
    const displayStatuses = ['queued', 'pending', 'running', 'downloading', 'processing', 'done', 'failed', 'canceled'];
    return [...tasksList]
      .filter(task => displayStatuses.includes(task.status))
      .sort((a, b) => {
        // Sort by created_at descending (or updated_at if available)
        const dateB = new Date(b.created_at || b.updated_at || 0).getTime();
        const dateA = new Date(a.created_at || a.updated_at || 0).getTime();
        return dateB - dateA;
      });
  }, [tasksList]);

  const toggleRow = (id: number) => {
    const newExpanded = new Set(expandedRows);
    if (newExpanded.has(id)) {
      newExpanded.delete(id);
    } else {
      newExpanded.add(id);
    }
    setExpandedRows(newExpanded);
  };

  const getStatusBadge = (status: TaskRecord['status']) => {
    switch (status) {
      case 'queued' as any:
      case 'pending':
        return <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300"><Clock className="w-3.5 h-3.5" /> 等待中</span>;
      case 'downloading':
        return <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"><RefreshCw className="w-3.5 h-3.5 animate-spin" /> 下載中</span>;
      case 'processing':
      case 'running' as any:
        return <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400"><RefreshCw className="w-3.5 h-3.5 animate-spin" /> 處理中</span>;
      case 'done':
        return <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400"><CheckCircle className="w-3.5 h-3.5" /> 已完成</span>;
      case 'failed' as any:
        return <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"><XCircle className="w-3.5 h-3.5" /> 失敗</span>;
      case 'canceled' as any:
        return <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400"><XCircle className="w-3.5 h-3.5" /> 已取消</span>;
      default:
        return <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300">未知</span>;
    }
  };

  const formatDate = (dateString: string) => {
    try {
      const d = new Date(dateString);
      if (isNaN(d.getTime())) return dateString;
      return d.toLocaleString('zh-TW', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return dateString;
    }
  };

  const downloadUrl = (taskId: number, format?: string) => {
    const baseUrl = import.meta.env.VITE_API_URL || '/api';
    const normalizedBaseUrl = baseUrl.endsWith('/') ? baseUrl.slice(0, -1) : baseUrl;
    const token = localStorage.getItem('auth_token');
    const url = `${normalizedBaseUrl}/tasks/${taskId}/download`;
    const queryParams = new URLSearchParams();
    if (format) queryParams.append('format', format);
    if (token) queryParams.append('token', token);
    const queryString = queryParams.toString();
    return queryString ? `${url}?${queryString}` : url;
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">任務追蹤</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">查看所有語音轉錄任務進度與下載結果</p>
        </div>
        <button
          onClick={manualRefresh}
          disabled={loading}
          data-testid="btn-refresh"
          className="flex items-center gap-2 px-4 py-2 bg-white dark:bg-[#161b22] border border-gray-200 dark:border-gray-800 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-50 transition-colors shadow-sm"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-blue-500' : 'text-gray-500'}`} />
          {loading ? '更新中...' : '手動更新'}
        </button>
      </div>

      {error ? (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-4 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="text-sm font-medium text-red-800 dark:text-red-400">無法載入任務資料</h3>
            <p className="text-sm text-red-600 dark:text-red-500 mt-1">{error.message}</p>
          </div>
        </div>
      ) : tasks.length === 0 && !loading ? (
        <div className="bg-white dark:bg-[#161b22] border border-gray-200 dark:border-gray-800 rounded-xl p-12 text-center shadow-sm">
          <FileAudio className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">目前沒有任務</h3>
          <p className="text-sm text-gray-500 dark:text-gray-400 max-w-sm mx-auto">
            您尚未提交任何轉錄任務，或是任務資料已被清除。請前往「提交任務」開始使用。
          </p>
        </div>
      ) : (
        <div className="bg-white dark:bg-[#161b22] border border-gray-200 dark:border-gray-800 rounded-xl shadow-sm overflow-hidden">
          <div className="overflow-x-auto w-full">
            <table data-testid="task-list-table" className="w-full text-left border-collapse whitespace-nowrap">
              <thead>
                <tr className="bg-slate-50 dark:bg-slate-800/50 border-b border-gray-200 dark:border-gray-800 text-sm font-medium text-gray-500 dark:text-gray-400">
                  <th className="px-6 py-4 w-8"></th>
                  <th className="px-6 py-4">影音名稱</th>
                  <th className="px-6 py-4">狀態</th>
                  <th className="px-6 py-4 text-right">更新時間</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-800 text-sm">
                {tasks.map((task) => {
                  const isExpanded = expandedRows.has(task.id);
                  const isDone = task.status === 'done';
                  const isError = task.status === 'failed' || task.status === 'canceled';

                  return (
                    <React.Fragment key={task.id}>
                      <tr
                        data-testid={`task-item-${task.id}`}
                        className={`hover:bg-slate-50 dark:hover:bg-slate-800/30 transition-colors cursor-pointer ${isExpanded ? 'bg-slate-50 dark:bg-slate-800/30' : ''}`}
                        onClick={() => toggleRow(task.id)}
                      >
                        <td className="px-6 py-4 text-gray-400">
                          {isExpanded ? <ChevronDown className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
                        </td>
                        <td className="px-6 py-4 font-medium flex-1 min-w-0 max-w-[200px] md:max-w-md">
                          <div className="flex items-center gap-3">
                            <FileText className="w-5 h-5 text-blue-500 flex-shrink-0" />
                            <div className="min-w-0">
                              <span className="truncate block text-gray-900 dark:text-gray-100" title={task.title || task.id}>
                                {task.title || '未知標題'}
                              </span>
                              <span className="text-[12px] text-gray-400 dark:text-gray-500 block font-mono mt-0.5 truncate" title={String(task.id)}>
                                ID: {task.id}
                              </span>
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-4" data-testid={`task-status-${task.id}`}>
                          {getStatusBadge(task.status)}
                        </td>
                        <td className="px-6 py-4 text-gray-500 dark:text-gray-400 text-right font-mono text-[13px]">
                          {formatDate(task.updated_at || task.created_at)}
                        </td>
                      </tr>

                      {/* Expanded Details Row */}
                      {isExpanded && (
                        <tr className="bg-slate-50/50 dark:bg-slate-800/10 border-b border-gray-100 dark:border-gray-800">
                          <td colSpan={4} className="px-6 py-4 pl-14">
                            <div className="space-y-4">
                              {/* Source URL */}
                              <div>
                                <h4 className="text-[11px] font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-1">來源網址</h4>
                                <a
                                  href={task.url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-sm text-blue-600 dark:text-blue-400 hover:underline break-all"
                                  onClick={(e) => e.stopPropagation()}
                                >
                                  {task.url}
                                </a>
                              </div>

                              {/* Error Message */}
                              {isError && task.error && (
                                <div className="p-3 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-100 dark:border-red-800">
                                  <h4 className="text-[11px] font-semibold text-red-800 dark:text-red-400 uppercase tracking-wider mb-1">錯誤訊息</h4>
                                  <p className="text-sm text-red-600 dark:text-red-300 font-mono text-xs">{task.error}</p>
                                </div>
                              )}

                              {/* Download Actions */}
                              {isDone && (
                                <div className="pt-2 border-t border-gray-200 dark:border-gray-700">
                                  <h4 className="text-[11px] font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3">下載結果</h4>

                                  <div className="flex flex-wrap gap-2">
                                    <a
                                      href={downloadUrl(task.id)}
                                      data-testid="btn-download-all"
                                      className="inline-flex items-center gap-2 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-md shadow-sm transition-colors"
                                      onClick={(e) => e.stopPropagation()}
                                    >
                                      <Download className="w-4 h-4" />
                                      下載全部 (Zip)
                                    </a>

                                    <div className="flex items-center gap-2 px-3 py-1.5 bg-white dark:bg-[#161b22] border border-gray-200 dark:border-gray-700 rounded-md shadow-sm">
                                      <span className="text-sm text-gray-600 dark:text-gray-300 mr-1">單獨格式:</span>

                                      {['txt', 'srt', 'vtt', 'json', 'tsv'].map((format) => (
                                        <a
                                          key={format}
                                          href={downloadUrl(task.id, format)}
                                          className="text-xs font-medium text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 uppercase px-1.5 py-0.5 rounded hover:bg-blue-50 dark:hover:bg-blue-900/30 transition-colors"
                                          onClick={(e) => e.stopPropagation()}
                                          title={`下載 ${format.toUpperCase()} 格式`}
                                        >
                                          {format}
                                        </a>
                                      ))}
                                    </div>
                                  </div>
                                </div>
                              )}

                              {/* Cancel Action */}
                              {!isDone && !isError && (
                                <div className="pt-2 border-t border-gray-200 dark:border-gray-700">
                                  <h4 className="text-[11px] font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">任務操作</h4>
                                  <button
                                    onClick={(e) => { e.stopPropagation(); handleCancel(task.id); }}
                                    disabled={cancellingId === task.id}
                                    className="inline-flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-red-600 hover:text-white hover:bg-red-600 border border-red-200 hover:border-red-600 rounded-md transition-all disabled:opacity-50"
                                  >
                                    {cancellingId === task.id ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                                    {cancellingId === task.id ? '取消中...' : '取消任務'}
                                  </button>
                                </div>
                              )}
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
