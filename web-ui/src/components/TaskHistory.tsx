import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Clock, FileText, CheckCircle, AlertCircle, Download } from 'lucide-react';

const API_BASE = `http://${window.location.hostname}:8002/api`;

interface TaskHistoryItem {
    id: number;
    title: string;
    status: string;
    created_at: string;
    requester: string;
}

export default function TaskHistory() {
    const [tasks, setTasks] = useState<TaskHistoryItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchHistory = async () => {
            try {
                const response = await axios.get(`${API_BASE}/tasks/history`);
                setTasks(response.data);
            } catch (err) {
                setError('無法載入任務歷史記錄');
                console.error(err);
            } finally {
                setLoading(false);
            }
        };
        fetchHistory();
    }, []);

    if (loading) return <div className="text-slate-400 py-8 text-center">正在載入歷史記錄...</div>;
    if (error) return <div className="text-red-500 py-8 text-center">{error}</div>;

    return (
        <div className="bg-white dark:bg-[#1c2128] rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden">
            <div className="p-5 border-b border-slate-100 dark:border-slate-800">
                <h2 className="font-semibold text-lg">任務歷史記錄</h2>
            </div>
            <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                    <thead className="bg-slate-50 dark:bg-slate-800/50">
                        <tr className="text-xs text-slate-500 dark:text-slate-400">
                            <th className="px-5 py-3">任務名稱</th>
                            <th className="px-5 py-3">狀態</th>
                            <th className="px-5 py-3">建立時間</th>
                            <th className="px-5 py-3 text-right">操作</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                        {tasks.map((task) => (
                            <tr key={task.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/30 transition-colors">
                                <td className="px-5 py-3 font-medium truncate max-w-[200px]" title={task.title}>{task.title}</td>
                                <td className="px-5 py-3">
                                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                                        task.status === 'DONE' ? 'bg-green-100 dark:bg-green-500/10 text-green-700 dark:text-green-400' :
                                        task.status === 'FAILED' ? 'bg-red-100 dark:bg-red-500/10 text-red-700 dark:text-red-400' :
                                        'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400'
                                    }`}>
                                        {task.status}
                                    </span>
                                </td>
                                <td className="px-5 py-3 text-slate-500 font-mono text-xs">
                                    {new Date(task.created_at).toLocaleString('zh-TW', { hour12: false })}
                                </td>
                                <td className="px-5 py-3 text-right">
                                    {task.status === 'DONE' && (
                                        <a
                                            href={`${API_BASE}/tasks/${task.id}/download`}
                                            className="inline-flex items-center space-x-1 text-indigo-500 hover:text-indigo-600 transition-colors"
                                            title="下載成果"
                                        >
                                            <Download size={16} />
                                        </a>
                                    )}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
            {tasks.length === 0 && (
                <div className="p-8 text-center text-slate-400">目前沒有歷史任務記錄。</div>
            )}
        </div>
    );
}
