import React from 'react';
import { useNavigate } from 'react-router-dom';
import { PlusCircle, FileAudio, LayoutDashboard } from 'lucide-react';

export const Dashboard: React.FC = () => {
  const navigate = useNavigate();

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

      <button
        onClick={() => navigate('/submit')}
        className="flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors shadow-sm"
      >
        <PlusCircle className="w-5 h-5" />
        提交任務
      </button>

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