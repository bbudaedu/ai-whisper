import React from 'react';
import { useNavigate } from 'react-router-dom';
import { PlusCircle, FileAudio, LayoutDashboard, History, Loader2 } from 'lucide-react';
import { usePolling } from '../hooks/usePolling';

export const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const { data: tasksList, loading } = usePolling<any[]>('tasks/history', 30000);

  const activeTasks = React.useMemo(() => {
    if (!tasksList || !Array.isArray(tasksList)) return [];
    const activeStatuses = ['queued', 'pending', 'running', 'downloading', 'processing'];
    return tasksList.filter(task => activeStatuses.includes(task.status));
  }, [tasksList]);

  if (loading && !tasksList) {
    return (
      <div className="h-full flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    );
  }

  const hasActiveTasks = activeTasks.length > 0;

  if (hasActiveTasks) {
    return (
      <div className="max-w-4xl mx-auto p-6 space-y-8">
        <div className="flex justify-between items-center">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">歡迎回來</h2>
          <button
            onClick={() => navigate('/submit')}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors shadow-sm"
          >
            <PlusCircle className="w-4 h-4" />
            提交新任務
          </button>
        </div>

        <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-100 dark:border-blue-800 p-6 rounded-2xl flex items-center gap-6">
          <div className="w-12 h-12 bg-blue-100 dark:bg-blue-800 rounded-xl flex items-center justify-center flex-shrink-0">
            <History className="w-6 h-6 text-blue-600 dark:text-blue-400" />
          </div>
          <div>
            <h3 className="font-bold text-gray-900 dark:text-white">您有 {activeTasks.length} 個進行中的任務</h3>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">您可以前往任務追蹤頁面查看詳細進度與下載結果。</p>
          </div>
          <button
            onClick={() => navigate('/track')}
            className="ml-auto text-sm font-bold text-blue-600 dark:text-blue-400 hover:underline"
          >
            立即查看
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto h-full flex flex-col items-center justify-center text-center p-6 min-h-[60vh]">
      <div className="w-20 h-20 bg-gray-100 dark:bg-gray-800 rounded-full flex items-center justify-center mb-6">
        <LayoutDashboard className="w-10 h-10 text-gray-400 dark:text-gray-500" />
      </div>

      <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-3">
        尚未建立任何任務
      </h2>

      <p className="text-gray-500 dark:text-gray-400 mb-8 max-w-md">
        尚未建立任何任務，開始提交音檔或 YouTube 連結。
      </p>

      <div className="flex flex-wrap gap-4 justify-center">
        <button
          onClick={() => navigate('/submit')}
          className="flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors shadow-sm"
        >
          <PlusCircle className="w-5 h-5" />
          提交任務
        </button>
        <button
          onClick={() => navigate('/history')}
          className="flex items-center gap-2 px-6 py-3 bg-white dark:bg-[#161b22] border border-gray-200 dark:border-gray-800 text-gray-700 dark:text-gray-200 font-medium rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors shadow-sm"
        >
          <History className="w-5 h-5" />
          查看歷史
        </button>
      </div>

      {/* Placeholder for future recent tasks / quick stats */}
      <div className="mt-16 grid grid-cols-1 sm:grid-cols-2 gap-4 w-full max-w-2xl opacity-50 pointer-events-none">
        <div className="bg-white dark:bg-[#161b22] p-5 rounded-xl border border-gray-200 dark:border-gray-800 text-left flex items-start gap-4">
          <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
            <FileAudio className="w-6 h-6 text-gray-400" />
          </div>
          <div>
            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-24 mb-2"></div>
            <div className="h-3 bg-gray-100 dark:bg-gray-800 rounded w-32"></div>
          </div>
        </div>
        <div className="bg-white dark:bg-[#161b22] p-5 rounded-xl border border-gray-200 dark:border-gray-800 text-left flex items-start gap-4">
          <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
            <FileAudio className="w-6 h-6 text-gray-400" />
          </div>
          <div>
            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-24 mb-2"></div>
            <div className="h-3 bg-gray-100 dark:bg-gray-800 rounded w-32"></div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
