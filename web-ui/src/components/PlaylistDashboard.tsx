import { useState } from 'react';
import {
    ListVideo, CheckCircle, Clock, ChevronDown, ChevronUp,
    Activity, FileText, Zap, CircleDot, Send, FileSearch, Brain, Layout, Image
} from 'lucide-react';
import axios from 'axios';
import { DashboardData, PlaylistData, VideoInfo } from '../types';
import NotebookLMStatsCard from './NotebookLMStatsCard';

const API_BASE = `http://${window.location.hostname}:8002/api`;

function formatTime(isoStr: string): string {
    if (!isoStr) return '—';
    try {
        const cleaned = isoStr.replace('_recovered', '');
        const d = new Date(cleaned);
        if (isNaN(d.getTime())) return isoStr;
        return d.toLocaleString('zh-TW', { hour12: false });
    } catch {
        return isoStr;
    }
}

function ProgressBar({ whispered, proofread, total }: { whispered: number; proofread: number; total: number }) {
    const displayTotal = total > 0 ? total : whispered;
    if (displayTotal === 0) {
        return (
            <div className="w-full h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                <div className="h-full bg-slate-300 dark:bg-slate-600 rounded-full" style={{ width: '0%' }} />
            </div>
        );
    }
    const pctWhispered = Math.round((whispered / displayTotal) * 100);
    const pctProofread = Math.round((proofread / displayTotal) * 100);
    return (
        <div className="space-y-1">
            <div className="w-full h-2.5 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden relative">
                <div
                    className="h-full rounded-full absolute left-0 top-0 transition-all duration-500"
                    style={{ width: `${pctWhispered}%`, background: 'linear-gradient(90deg, #3B82F6, #60A5FA)' }}
                />
                <div
                    className="h-full rounded-full absolute left-0 top-0 transition-all duration-500"
                    style={{ width: `${pctProofread}%`, background: 'linear-gradient(90deg, #10B981, #34D399)' }}
                />
            </div>
            <div className="flex justify-between text-xs text-slate-500 dark:text-slate-400 font-mono mt-1">
                <span>{proofread}/{displayTotal} 校對完成 ({pctProofread}%)</span>
                <span></span>
            </div>
        </div>
    );
}

function KpiCard({ icon: Icon, label, value, accent }: {
    icon: React.ElementType;
    label: string;
    value: number | string;
    accent: string;
}) {
    return (
        <div className="bg-white dark:bg-[#1c2128] rounded-2xl p-5 border border-slate-200 dark:border-slate-800 shadow-sm flex items-center space-x-4">
            <div className={`w-11 h-11 rounded-xl flex items-center justify-center ${accent}`}>
                <Icon size={20} />
            </div>
            <div>
                <div className="text-2xl font-bold font-mono tracking-tight">{value}</div>
                <div className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{label}</div>
            </div>
        </div>
    );
}

function PlaylistCard({ pl, isExpanded, onToggle }: {
    pl: PlaylistData;
    isExpanded: boolean;
    onToggle: () => void;
}) {
    const isLegacy = pl.id === '__legacy__';
    return (
        <div className="bg-white dark:bg-[#1c2128] rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden transition-all duration-200 hover:shadow-md">
            {/* Card Header */}
            <div
                className="p-5 cursor-pointer select-none"
                onClick={onToggle}
            >
                <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center space-x-3 min-w-0">
                        <div className={`w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 ${isLegacy
                            ? 'bg-slate-100 dark:bg-slate-800 text-slate-500'
                            : pl.enabled
                                ? 'bg-blue-50 dark:bg-blue-500/10 text-[#3B82F6]'
                                : 'bg-slate-100 dark:bg-slate-800 text-slate-400'
                            }`}>
                            <ListVideo size={18} />
                        </div>
                        <div className="min-w-0">
                            <h3 className="font-semibold text-sm truncate">{pl.name}</h3>
                            {pl.whisper_model && (
                                <span className="text-xs text-slate-400 font-mono">{pl.whisper_model}</span>
                            )}
                        </div>
                    </div>
                    <div className="flex items-center space-x-2 flex-shrink-0">
                        {!isLegacy && (
                            <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${pl.enabled
                                ? 'bg-green-100 dark:bg-green-500/10 text-green-700 dark:text-green-400'
                                : 'bg-slate-100 dark:bg-slate-800 text-slate-500'
                                }`}>
                                {pl.enabled ? '啟用' : '停用'}
                            </span>
                        )}
                        {isExpanded ? <ChevronUp size={16} className="text-slate-400" /> : <ChevronDown size={16} className="text-slate-400" />}
                    </div>
                </div>

                {/* Stats Row */}
                <div className="grid grid-cols-3 gap-3 mb-3">
                    <div className="text-center">
                        <div className="text-lg font-bold font-mono text-[#3B82F6]">{pl.stats.whispered}</div>
                        <div className="text-xs text-slate-500">已轉錄</div>
                    </div>
                    <div className="text-center">
                        <div className="text-lg font-bold font-mono text-emerald-500">{pl.stats.proofread}</div>
                        <div className="text-xs text-slate-500">已校對</div>
                    </div>
                    <div className="text-center">
                        <div className={`text-lg font-bold font-mono ${pl.stats.pending > 0 ? 'text-[#F97316]' : 'text-slate-400'}`}>{pl.stats.pending}</div>
                        <div className="text-xs text-slate-500">待校對</div>
                    </div>
                </div>

                {/* Progress Bar */}
                <ProgressBar whispered={pl.stats.whispered} proofread={pl.stats.proofread} total={pl.total_videos} />

                {pl.last_processed_at && (
                    <div className="text-xs text-slate-400 mt-2 flex items-center space-x-1">
                        <Clock size={12} />
                        <span>最後處理: {formatTime(pl.last_processed_at)}</span>
                    </div>
                )}
            </div>

            {/* Expanded Detail Table */}
            {isExpanded && pl.videos.length > 0 && (
                <div className="border-t border-slate-100 dark:border-slate-800">
                    <div className="overflow-x-auto max-h-80 overflow-y-auto">
                        <table className="w-full text-left text-sm">
                            <thead className="bg-slate-50 dark:bg-slate-800/50 sticky top-0">
                                <tr className="text-xs text-slate-500 dark:text-slate-400">
                                    <th className="px-5 py-2.5">影片名稱</th>
                                    <th className="px-5 py-2.5">Whisper</th>
                                    <th className="px-5 py-2.5">校對</th>
                                    <th className="px-5 py-2.5">NotebookLM</th>
                                    <th className="px-5 py-2.5">時間</th>
                                    <th className="px-5 py-2.5 text-right">操作</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                                {pl.videos
                                    .sort((a: VideoInfo, b: VideoInfo) => {
                                        const numA = parseInt((a.title || '').match(/(\d+)\s*$/)?.[1] || '0', 10);
                                        const numB = parseInt((b.title || '').match(/(\d+)\s*$/)?.[1] || '0', 10);
                                        return numA - numB;
                                    })
                                    .map((v) => (
                                        <tr key={v.video_id} className="hover:bg-slate-50 dark:hover:bg-slate-800/30 transition-colors text-sm">
                                            <td className="px-5 py-2.5">
                                                <div className="flex items-center space-x-2">
                                                    <FileText size={14} className="text-[#3B82F6] flex-shrink-0" />
                                                    <span className="truncate max-w-[150px]" title={v.title}>{v.title}</span>
                                                </div>
                                            </td>
                                            <td className="px-5 py-2.5">
                                                <span className="inline-flex items-center space-x-1 text-green-600 dark:text-green-400">
                                                    <CheckCircle size={13} />
                                                    <span className="text-xs">完成</span>
                                                </span>
                                            </td>
                                            <td className="px-5 py-2.5">
                                                {v.proofread ? (
                                                    <span className="inline-flex items-center space-x-1 text-green-600 dark:text-green-400">
                                                        <CheckCircle size={13} />
                                                        <span className="text-xs">完成</span>
                                                    </span>
                                                ) : (
                                                    <span className="inline-flex items-center space-x-1 text-slate-400">
                                                        <Clock size={13} />
                                                        <span className="text-xs">待處理</span>
                                                    </span>
                                                )}
                                            </td>
                                            <td className="px-5 py-2.5">
                                                {v.notebooklm_output ? (
                                                    <div className="flex items-center gap-1.5">
                                                        {v.notebooklm_output.mindmap && (
                                                            <a 
                                                                href={`${API_BASE}/notebooklm/download?episode=${pl.folder_prefix || 'T097V'}${v.title.match(/(\d+)\s*$/)?.[1].padStart(3, '0')}&filename=${pl.folder_prefix || 'T097V'}${v.title.match(/(\d+)\s*$/)?.[1].padStart(3, '0')}_mindmap.md`}
                                                                target="_blank" rel="noreferrer"
                                                                className="w-6 h-6 rounded bg-indigo-50 dark:bg-indigo-500/10 text-indigo-500 flex items-center justify-center hover:bg-indigo-100 transition-colors"
                                                                title="心智圖"
                                                            >
                                                                <Brain size={12} />
                                                            </a>
                                                        )}
                                                        {v.notebooklm_output.presentation && (
                                                            <a 
                                                                href={`${API_BASE}/notebooklm/download?episode=${pl.folder_prefix || 'T097V'}${v.title.match(/(\d+)\s*$/)?.[1].padStart(3, '0')}&filename=${pl.folder_prefix || 'T097V'}${v.title.match(/(\d+)\s*$/)?.[1].padStart(3, '0')}_presentation.md`}
                                                                target="_blank" rel="noreferrer"
                                                                className="w-6 h-6 rounded bg-blue-50 dark:bg-blue-500/10 text-blue-500 flex items-center justify-center hover:bg-blue-100 transition-colors"
                                                                title="簡報綱要"
                                                            >
                                                                <Layout size={12} />
                                                            </a>
                                                        )}
                                                        {v.notebooklm_output.summary && (
                                                            <a 
                                                                href={`${API_BASE}/notebooklm/download?episode=${pl.folder_prefix || 'T097V'}${v.title.match(/(\d+)\s*$/)?.[1].padStart(3, '0')}&filename=${pl.folder_prefix || 'T097V'}${v.title.match(/(\d+)\s*$/)?.[1].padStart(3, '0')}_summary.md`}
                                                                target="_blank" rel="noreferrer"
                                                                className="w-6 h-6 rounded bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 flex items-center justify-center hover:bg-emerald-100 transition-colors"
                                                                title="影片摘要"
                                                            >
                                                                <FileSearch size={12} />
                                                            </a>
                                                        )}
                                                        {(v.notebooklm_output.infographic_standard || v.notebooklm_output.infographic_compact) && (
                                                            <a 
                                                                href={`${API_BASE}/notebooklm/download?episode=${pl.folder_prefix || 'T097V'}${v.title.match(/(\d+)\s*$/)?.[1].padStart(3, '0')}&filename=${pl.folder_prefix || 'T097V'}${v.title.match(/(\d+)\s*$/)?.[1].padStart(3, '0')}_infographic_full.md`}
                                                                target="_blank" rel="noreferrer"
                                                                className="w-6 h-6 rounded bg-amber-50 dark:bg-amber-500/10 text-amber-600 flex items-center justify-center hover:bg-amber-100 transition-colors"
                                                                title="資訊圖表"
                                                            >
                                                                <Image size={12} />
                                                            </a>
                                                        )}
                                                        {!Object.values(v.notebooklm_output).some(Boolean) && (
                                                            <span className="text-xs text-slate-300 dark:text-slate-600">無產出</span>
                                                        )}
                                                    </div>
                                                ) : (
                                                    <span className="text-xs text-slate-300 dark:text-slate-600">—</span>
                                                )}
                                            </td>
                                            <td className="px-5 py-2.5 text-xs text-slate-500 font-mono whitespace-nowrap">
                                                {formatTime(v.processed_at)}
                                            </td>
                                            <td className="px-5 py-2.5 text-right">
                                                <button 
                                                    onClick={(e) => {
                                                        e.stopPropagation();
                                                        axios.post(`${API_BASE}/notebooklm/trigger`, { episode: `${pl.folder_prefix || 'T097V'}${v.title.match(/(\d+)\s*$/)?.[1].padStart(3, '0')}` });
                                                    }}
                                                    className="p-1.5 rounded-lg hover:bg-indigo-50 dark:hover:bg-indigo-500/10 text-indigo-500 transition-colors"
                                                    title="觸發 NotebookLM 後製"
                                                >
                                                    <Send size={14} />
                                                </button>
                                            </td>
                                        </tr>
                                    ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {isExpanded && pl.videos.length === 0 && (
                <div className="border-t border-slate-100 dark:border-slate-800 p-5 text-center text-sm text-slate-400">
                    尚無已處理的影片
                </div>
            )}
        </div>
    );
}

export default function PlaylistDashboard({ data }: { data: DashboardData | null }) {
    const [expandedId, setExpandedId] = useState<string | null>(null);

    if (!data) {
        return (
            <div className="flex items-center justify-center py-16 text-slate-400">
                <Activity size={20} className="animate-pulse mr-2" />
                <span>正在載入 Dashboard 資料...</span>
            </div>
        );
    }

    const { playlists, global_stats } = data;

    const sortedPlaylists = [...playlists].sort((a: PlaylistData, b: PlaylistData) => {
        // Sort by enabled status (enabled first), then by name
        if (a.enabled && !b.enabled) return -1;
        if (!a.enabled && b.enabled) return 1;
        return a.name.localeCompare(b.name);
    });

    return (
        <div className="space-y-6">
            <NotebookLMStatsCard status={data.notebooklm} />
            
            {/* KPI Summary Row */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <KpiCard
                    icon={ListVideo}
                    label="播放清單總數"
                    value={global_stats.total_playlists}
                    accent="bg-blue-50 dark:bg-blue-500/10 text-[#3B82F6]"
                />
                <KpiCard
                    icon={Zap}
                    label="啟用中"
                    value={global_stats.active_playlists}
                    accent="bg-emerald-50 dark:bg-emerald-500/10 text-emerald-500"
                />
                <KpiCard
                    icon={CircleDot}
                    label="已處理影片"
                    value={global_stats.total_videos}
                    accent="bg-indigo-50 dark:bg-indigo-500/10 text-indigo-500"
                />
                <KpiCard
                    icon={CheckCircle}
                    label="已校對完成"
                    value={global_stats.total_proofread}
                    accent="bg-amber-50 dark:bg-amber-500/10 text-amber-600"
                />
            </div>

            {/* Playlist Cards Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {sortedPlaylists.map((pl) => (
                    <PlaylistCard
                        key={pl.id}
                        pl={pl}
                        isExpanded={expandedId === pl.id}
                        onToggle={() => setExpandedId(expandedId === pl.id ? null : pl.id)}
                    />
                ))}
            </div>

            {sortedPlaylists.length === 0 && (
                <div className="text-center py-12 text-slate-400">
                    <ListVideo size={40} className="mx-auto mb-3 opacity-40" />
                    <p>尚未新增任何播放清單。請到「系統設定」新增。</p>
                </div>
            )}
        </div>
    );
}
