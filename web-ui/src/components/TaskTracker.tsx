import { FileText, CheckCircle, Clock } from 'lucide-react';

export default function TaskTracker({ stats }: { stats: Record<string, any> }) {
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
        <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
                <thead>
                    <tr className="bg-slate-50 dark:bg-slate-800/50 border-b border-slate-200 dark:border-slate-800 text-sm font-medium text-slate-500 dark:text-slate-400">
                        <th className="px-6 py-4">影音名稱</th>
                        <th className="px-6 py-4">處理狀態 (Whisper)</th>
                        <th className="px-6 py-4">校對狀態 (Proofread)</th>
                        <th className="px-6 py-4">更新時間</th>
                    </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800 text-sm">
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

                        return (
                            <tr key={i} className="hover:bg-slate-50 dark:hover:bg-slate-800/30 transition-colors">
                                <td className="px-6 py-4 font-medium flex items-center space-x-2">
                                    <FileText size={16} className="text-indigo-500 flex-shrink-0" />
                                    <span className="truncate max-w-[200px] md:max-w-xs block" title={info.title || id}>
                                        {info.title || id}
                                        <span className="text-xs text-slate-400 dark:text-slate-500 block">ID: {id}</span>
                                    </span>
                                </td>
                                <td className="px-6 py-4">
                                    <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-full bg-green-100 dark:bg-green-500/10 text-green-700 dark:text-green-400 text-xs font-medium">
                                        <CheckCircle size={12} />
                                        <span>已轉錄</span>
                                    </span>
                                </td>
                                <td className="px-6 py-4">
                                    {info.proofread ? (
                                        <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-full bg-green-100 dark:bg-green-500/10 text-green-700 dark:text-green-400 text-xs font-medium">
                                            <CheckCircle size={12} />
                                            <span>校對完畢</span>
                                        </span>
                                    ) : (
                                        <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 text-xs font-medium">
                                            <Clock size={12} />
                                            <span>尚未校對或處理中</span>
                                        </span>
                                    )}
                                </td>
                                <td className="px-6 py-4 text-slate-500">
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
