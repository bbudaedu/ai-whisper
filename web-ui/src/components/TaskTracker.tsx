import { FileText, CheckCircle, Clock } from 'lucide-react';
import { EpisodeRecord } from '../types';

export default function TaskTracker({ stats }: { stats: Record<string, EpisodeRecord> }) {
    // 從標題中提取集數數字，依照集數排序 (1, 2, 3...)
    const entries = Object.entries(stats).sort(([, a], [, b]) => {
        const numA = parseInt((a.title || '').match(/(\d+)\s*$/)?.[1] || '0', 10);
        const numB = parseInt((b.title || '').match(/(\d+)\s*$/)?.[1] || '0', 10);
        return numA - numB;
    });

    if (entries.length === 0) {
        return (
            <div className="p-8 text-center text-slate-500">
                目前沒有已經處理的影片紀錄。
            </div>
        );
    }

    return (
        <div className="overflow-x-auto w-full">
            <table className="w-full text-left border-collapse whitespace-nowrap">
                <thead>
                    <tr className="bg-slate-50 dark:bg-slate-800/50 border-b border-slate-200 dark:border-slate-800 text-base font-medium text-slate-500 dark:text-slate-400">
                        <th className="px-6 py-4">影音名稱</th>
                        <th className="px-6 py-4 text-center">進度</th>
                        <th className="px-6 py-4 text-right">更新時間</th>
                    </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800 text-base">
                    {entries.map(([id, info], i) => {
                        let TimeDisplay = "未知";
                        if (info.processed_at && info.processed_at !== "N/A") {
                            try {
                                const cleaned = info.processed_at.replace("_recovered", "");
                                const d = new Date(cleaned);
                                if (!isNaN(d.getTime())) {
                                    TimeDisplay = d.toLocaleString('zh-TW', { hour12: false });
                                } else {
                                    TimeDisplay = info.processed_at;
                                }
                            } catch {
                                TimeDisplay = info.processed_at;
                            }
                        }

                        // Check actual episode status
                        const isDownloaded = info.downloaded === true || info.transcribed === true || info.proofread === true;
                        const isWhispered = info.transcribed === true || info.proofread === true;
                        const isProofread = info.proofread === true;

                        return (
                            <tr key={i} className="hover:bg-slate-50 dark:hover:bg-slate-800/30 transition-colors">
                                <td className="px-6 py-4 font-medium flex-1 min-w-0">
                                    <div className="flex items-center space-x-3">
                                        <FileText size={20} className="text-indigo-500 flex-shrink-0" />
                                        <div className="min-w-0">
                                            <span className="truncate block text-slate-700 dark:text-slate-200" title={info.title || id}>
                                                {info.title || id}
                                            </span>
                                            <span className="text-[14px] text-slate-400 dark:text-slate-500 block font-mono mt-0.5">ID: {id}</span>
                                        </div>
                                    </div>
                                </td>
                                <td className="px-6 py-4">
                                    <div className="flex items-center justify-center space-x-4 bg-slate-50/50 dark:bg-[#161b22] rounded-xl py-2.5 px-5 shadow-sm border border-slate-100 dark:border-slate-800 w-fit mx-auto">
                                        <div className="flex items-center space-x-1.5" title="下載">
                                            {isDownloaded ? <CheckCircle size={18} className="text-emerald-500" /> : <Clock size={18} className="text-slate-300" />}
                                            <span className={`text-[15px] ${isDownloaded ? 'text-emerald-600 dark:text-emerald-400 font-medium' : 'text-slate-400'}`}>下載</span>
                                        </div>
                                        <span className="text-slate-200 dark:text-slate-700">|</span>
                                        <div className="flex items-center space-x-1.5" title="轉錄">
                                            {isWhispered ? <CheckCircle size={18} className="text-emerald-500" /> : <Clock size={18} className="text-slate-300" />}
                                            <span className={`text-[15px] ${isWhispered ? 'text-emerald-600 dark:text-emerald-400 font-medium' : 'text-slate-400'}`}>轉錄</span>
                                        </div>
                                        <span className="text-slate-200 dark:text-slate-700">|</span>
                                        <div className="flex items-center space-x-1.5" title="校對">
                                            {isProofread ? <CheckCircle size={18} className="text-emerald-500" /> : <Clock size={18} className="text-slate-300" />}
                                            <span className={`text-[15px] ${isProofread ? 'text-emerald-600 dark:text-emerald-400 font-medium' : 'text-slate-400'}`}>校對</span>
                                        </div>
                                    </div>
                                </td>
                                <td className="px-6 py-4 text-slate-500 text-right font-mono">
                                    {TimeDisplay}
                                </td>
                            </tr>
                        )
                    })}
                </tbody>
            </table>
        </div>
    );
}
