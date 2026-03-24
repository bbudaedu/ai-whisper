import { Share2, HelpCircle, HardDrive, ListOrdered, Calendar } from 'lucide-react';
import { NotebookLMStatus } from '../types';

export default function NotebookLMStatsCard({ status }: { status?: NotebookLMStatus }) {
    if (!status) return null;

    const usedPct = Math.round((status.used_quota / status.total_quota) * 100);
    const accentColor = usedPct > 80 ? 'text-red-500' : usedPct > 50 ? 'text-amber-500' : 'text-emerald-500';
    const bgColor = usedPct > 80 ? 'bg-red-50 dark:bg-red-500/10' : usedPct > 50 ? 'bg-amber-50 dark:bg-amber-500/10' : 'bg-emerald-50 dark:bg-emerald-500/10';

    return (
        <div className="bg-white dark:bg-[#1c2128] rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden mb-6">
            <div className="p-5 border-b border-slate-100 dark:border-slate-800 flex justify-between items-center">
                <div className="flex items-center space-x-2">
                    <Share2 className="text-indigo-500" size={18} />
                    <h2 className="text-lg font-semibold">NotebookLM 後製狀態</h2>
                </div>
                <div className="text-xs text-slate-400 flex items-center space-x-1">
                    <Calendar size={12} />
                    <span>今日配額已重置: 00:00</span>
                </div>
            </div>
            
            <div className="p-5">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    {/* Quota Progress */}
                    <div className="space-y-3">
                        <div className="flex justify-between items-end">
                            <span className="text-sm text-slate-500 dark:text-slate-400 flex items-center">
                                <HardDrive size={14} className="mr-1.5" />
                                每日查詢配額 (Daily Quota)
                            </span>
                            <span className={`text-sm font-bold font-mono ${accentColor}`}>
                                {status.used_quota} / {status.total_quota}
                            </span>
                        </div>
                        <div className="w-full h-2.5 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                            <div 
                                className={`h-full transition-all duration-1000 ${accentColor.replace('text-', 'bg-')}`} 
                                style={{ width: `${usedPct}%` }}
                            />
                        </div>
                        <p className="text-[10px] text-slate-400 italic">
                            * 每個帳號每日限額 50 次，超過將自動順延至隔日。
                        </p>
                    </div>

                    {/* Queue Status */}
                    <div className="flex items-center justify-around border-x border-slate-100 dark:border-slate-800 px-4">
                        <div className="text-center">
                            <div className="w-10 h-10 rounded-full bg-blue-50 dark:bg-blue-500/10 text-blue-500 flex items-center justify-center mx-auto mb-2">
                                <ListOrdered size={18} />
                            </div>
                            <div className="text-xl font-bold font-mono">{status.queue_size}</div>
                            <div className="text-[10px] text-slate-500 uppercase tracking-wider">佇列中</div>
                        </div>
                        <div className="text-center">
                            <div className="w-10 h-10 rounded-full bg-indigo-50 dark:bg-indigo-500/10 text-indigo-500 flex items-center justify-center mx-auto mb-2">
                                <Share2 size={18} className="animate-spin-slow" />
                            </div>
                            <div className="text-xl font-bold font-mono">{status.active_tasks}</div>
                            <div className="text-[10px] text-slate-500 uppercase tracking-wider">執行中</div>
                        </div>
                    </div>

                    {/* Info/Help */}
                    <div className={`${bgColor} rounded-xl p-4 flex items-start space-x-3`}>
                        <HelpCircle className={accentColor} size={18} />
                        <div className="text-xs space-y-2">
                            <p className="font-semibold">後製包含 5 種產出：</p>
                            <ul className="grid grid-cols-2 gap-x-2 gap-y-1 text-slate-600 dark:text-slate-400 opacity-80">
                                <li>• 心智圖 (Mermaid)</li>
                                <li>• 簡報綱要</li>
                                <li>• 影片摘要</li>
                                <li>• 資訊圖表</li>
                            </ul>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
