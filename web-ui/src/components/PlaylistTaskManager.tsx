import { useState, useCallback, useEffect } from 'react';
import axios from 'axios';
import { ListVideo, CircleDot, Play, Pause, Check, Clock, Loader2, Plus, Film, List, Settings, Save, Trash2, Edit2, X, Maximize2, Minimize2, Hash, FileText, ChevronDown, ChevronUp } from 'lucide-react';
import { EpisodeStatus, PlaylistData, UrlDetectResult, DashboardData } from '../types';

const API_BASE = `http://${window.location.hostname}:8002/api`;

/* ─── Helpers ───────────────────────────────────────── */

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

function StatusBadge({ status }: { status: string }) {
    const map: Record<string, { bg: string; text: string; label: string; dot: string }> = {
        idle: { bg: 'bg-slate-100 dark:bg-slate-800', text: 'text-slate-500', label: '閒置', dot: 'bg-slate-400' },
        running: { bg: 'bg-emerald-50 dark:bg-emerald-500/10', text: 'text-emerald-600 dark:text-emerald-400', label: '執行中', dot: 'bg-emerald-500 animate-pulse' },
        paused: { bg: 'bg-amber-50 dark:bg-amber-500/10', text: 'text-amber-600 dark:text-amber-400', label: '已暫停', dot: 'bg-amber-500' },
        error: { bg: 'bg-red-50 dark:bg-red-500/10', text: 'text-red-600 dark:text-red-400', label: '錯誤', dot: 'bg-red-500' },
    };
    const s = map[status] || map.idle;
    return (
        <span className={`inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${s.bg} ${s.text}`}>
            <span className={`w-2 h-2 rounded-full ${s.dot}`} />
            <span>{s.label}</span>
        </span>
    );
}



function StatusStep({ label, done, onClick }: { label: string, done: boolean, onClick: () => void }) {
    return (
        <div className="flex items-center space-x-1.5 group cursor-pointer px-1" onClick={onClick} title={`重做 ${label}`}>
            {done ? (
                <Check size={16} strokeWidth={3.5} className="text-emerald-500 group-hover:hidden" />
            ) : (
                <Clock size={14} className="text-slate-300 group-hover:hidden" />
            )}
            <X size={14} className="text-red-400 hidden group-hover:block" />
            <span className={`text-[13px] ${done ? 'text-emerald-600 dark:text-emerald-400 font-medium' : 'text-slate-400'}`}>{label}</span>
        </div>
    );
}

/* ─── Playlist Card ─────────────────────────────────── */

function PlaylistCard({ pl, isExpanded, onToggle, onControl, onUpdate, onDelete, isFullScreen, onToggleFullScreen }: {
    pl: PlaylistData;
    isExpanded: boolean;
    onToggle: () => void;
    onControl: (action: string) => void;
    onUpdate: (id: string, form: Record<string, unknown>) => void;
    onDelete: (id: string) => void;
    isFullScreen: boolean;
    onToggleFullScreen: () => void;
}) {


    const [isEditing, setIsEditing] = useState(false);
    const [isConfigExpanded, setIsConfigExpanded] = useState(false);
    const [editForm, setEditForm] = useState({
        whisper_lang: pl.whisper_lang || 'auto',
        whisper_prompt: pl.whisper_prompt || '',
        proofread_prompt: pl.proofread_prompt || '',
        lecture_pdf: pl.lecture_pdf || '',
        batch_size: pl.batch_size || 5,
        output_dir: pl.output_dir || '',
        whisper_model: pl.whisper_model || 'large-v2',
        folder_prefix: pl.folder_prefix || 'T097V',
        track: pl.track !== false,
    });

    const [episodes, setEpisodes] = useState<EpisodeStatus[] | null>(null);
    const [loadingEpisodes, setLoadingEpisodes] = useState(false);

    // Fetch episodes status when expanded
    useEffect(() => {
        if (isExpanded) {
            let isMounted = true;
            const fetchEpisodes = async () => {
                setLoadingEpisodes(true);
                try {
                    const res = await axios.get(`${API_BASE}/playlists/${pl.id}/episodes`);
                    if (isMounted) {
                        setEpisodes(res.data.episodes);
                    }
                } catch (e) {
                    console.error('Failed to fetch episodes', e);
                } finally {
                    if (isMounted) setLoadingEpisodes(false);
                }
            };
            fetchEpisodes();
            return () => { isMounted = false; };
        }
    }, [isExpanded, pl.id]);

    const handleSaveEdit = () => {
        onUpdate(pl.id, editForm);
        setIsEditing(false);
    };

    const handleRedo = async (videoId: string, targetStep?: string) => {
        let confirmMsg = `確定要重做這集嗎？這將會刪除該集的相關檔案並重新處理。`;
        if (targetStep) {
            confirmMsg = `確定要重做 [${targetStep}] 步驟嗎？這將刪除該步驟(包含)之後的所有產出檔案。`;
        }
        if (!confirm(confirmMsg)) return;

        try {
            await axios.post(`${API_BASE}/playlists/${pl.id}/episodes/${videoId}/redo`, { target_step: targetStep });

            // Refresh episodes list after successful redo
            setLoadingEpisodes(true);
            const res = await axios.get(`${API_BASE}/playlists/${pl.id}/episodes`);
            setEpisodes(res.data.episodes);
            setLoadingEpisodes(false);
        } catch (e) {
            console.error('Redo failed', e);
            alert('重做失敗，請查看伺服器日誌');
        }
    };

    return (
        <div className={`bg-white dark:bg-[#1c2128] rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden transition-all duration-300 ${isExpanded ? isFullScreen ? 'fixed inset-4 z-50 flex flex-col shadow-2xl' : 'row-span-2 shadow-md' : 'hover:shadow-md'
            }`}>
            {/* Card Header */}
            <div className="p-5">
                <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center space-x-3 min-w-0 cursor-pointer" onClick={onToggle}>
                        <div className={`w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 ${pl.enabled ? 'bg-blue-50 dark:bg-emerald-500/10 text-[#3B82F6]'
                            : 'bg-slate-100 dark:bg-slate-800 text-slate-400'
                            }`}>
                            <ListVideo size={18} />
                        </div>
                        <div className="min-w-0">
                            <h3 className="font-semibold text-sm truncate">{pl.name}</h3>
                            <div className="flex items-center space-x-2 mt-0.5">
                                <span className="text-xs text-slate-400 font-mono">{pl.whisper_model}</span>
                                {pl.batch_size !== undefined && pl.batch_size > 0 && (
                                    <span className="text-xs text-slate-400">· 每輪 {pl.batch_size} 集</span>
                                )}
                            </div>
                        </div>
                    </div>
                    <div className="flex items-center space-x-2 flex-shrink-0">
                        <StatusBadge status={pl.status} />
                        <div className="flex items-center space-x-1 ml-2">
                            {pl.status !== 'running' ? (
                                <button onClick={() => onControl('start')} className="p-1.5 rounded-lg hover:bg-emerald-50 dark:hover:bg-emerald-900/20 text-emerald-500 transition-colors" title="開始">
                                    <Play size={16} />
                                </button>
                            ) : (
                                <button onClick={() => onControl('pause')} className="p-1.5 rounded-lg hover:bg-amber-50 dark:hover:bg-amber-900/20 text-amber-500 transition-colors" title="暫停">
                                    <Pause size={16} />
                                </button>
                            )}
                        </div>
                        {isExpanded && (
                            <button onClick={(e) => { e.stopPropagation(); onToggleFullScreen(); }}
                                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                                title={isFullScreen ? "退出全螢幕" : "全螢幕放大"}>
                                {isFullScreen ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
                            </button>
                        )}
                        <span className="text-xs font-mono px-2 py-0.5 rounded-full bg-slate-100 dark:bg-[#0f172a] text-slate-500">
                            {pl.id}
                        </span>
                        <button onClick={onToggle} className="p-1 text-slate-400">
                            {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                        </button>
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
                        <div className={`text-lg font-bold font-mono ${pl.total_videos - pl.stats.proofread > 0 ? 'text-[#F97316]' : 'text-slate-400'}`}>{pl.total_videos - pl.stats.proofread}</div>
                        <div className="text-xs text-slate-500">待校對</div>
                    </div>
                </div>

                {pl.last_run && (
                    <div className="text-xs text-slate-400 mt-2 flex items-center space-x-1">
                        <Clock size={12} />
                        <span>最後處理: {formatTime(pl.last_run)}</span>
                    </div>
                )}
            </div>

            {/* Expanded Content */}
            {isExpanded && (
                <div className="border-t border-slate-100 dark:border-slate-800 flex-grow overflow-y-auto">
                    {/* Per-playlist Config Toggle */}
                    <div className="px-5 py-3 bg-slate-50/50 dark:bg-slate-900/30 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-800/50 transition-colors" onClick={() => setIsConfigExpanded(!isConfigExpanded)}>
                        <h4 className="text-[16px] font-semibold text-slate-700 dark:text-slate-300 flex items-center space-x-2">
                            <Settings size={16} className="text-[#3B82F6]" />
                            <span>清單專屬參數設定</span>
                        </h4>
                        <button className="p-1 text-slate-400 hover:text-slate-600 transition-colors">
                            {isConfigExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                        </button>
                    </div>

                    {isConfigExpanded && (
                        <div className="p-5 bg-slate-50/50 dark:bg-slate-900/20 space-y-4 border-b border-slate-100 dark:border-slate-800">
                            <div className="flex items-center justify-end">
                                <div className="flex items-center space-x-2">
                                    {isEditing ? (
                                        <>
                                            <button onClick={handleSaveEdit} className="text-sm bg-[#3B82F6] hover:bg-blue-600 text-white px-3 py-1.5 rounded-lg flex items-center space-x-1 transition-colors">
                                                <Save size={14} />
                                                <span>儲存</span>
                                            </button>
                                            <button onClick={() => setIsEditing(false)} className="text-sm px-3 py-1.5 rounded-lg text-slate-500 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors">取消</button>
                                        </>
                                    ) : (
                                        <>
                                            <button onClick={() => setIsEditing(true)} className="text-sm text-[#3B82F6] hover:bg-blue-50 dark:hover:bg-blue-900/20 px-3 py-1.5 rounded-lg flex items-center space-x-1 transition-colors">
                                                <Edit2 size={14} />
                                                <span>編輯設定</span>
                                            </button>
                                            <button onClick={() => onDelete(pl.id)} className="text-sm text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 px-3 py-1.5 rounded-lg flex items-center space-x-1 transition-colors">
                                                <Trash2 size={14} />
                                                <span>刪除</span>
                                            </button>
                                        </>
                                    )}
                                </div>
                            </div>

                            {isEditing ? (
                                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-2 gap-4">
                                    <div className="space-y-1.5">
                                        <div className="flex items-center justify-between">
                                            <label htmlFor={`whisper_prompt_${pl.id}`} className="text-sm font-semibold text-slate-600 dark:text-slate-400">Whisper Prompt</label>
                                            <span className="text-xs text-slate-400">引導模型識別特定專有名詞</span>
                                        </div>
                                        <textarea
                                            id={`whisper_prompt_${pl.id}`}
                                            value={editForm.whisper_prompt}
                                            onChange={e => setEditForm({ ...editForm, whisper_prompt: e.target.value })}
                                            rows={4}
                                            className="w-full bg-white dark:bg-[#0f172a] border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-base focus:ring-2 focus:ring-[#3B82F6] outline-none resize-y min-h-[100px]"
                                            placeholder="例如：提婆達多、舍利弗、阿難..."
                                        />
                                    </div>
                                    <div className="space-y-1.5">
                                        <div className="flex items-center justify-between">
                                            <div className="flex items-center space-x-2">
                                                <label htmlFor={`proofread_prompt_${pl.id}`} className="text-sm font-semibold text-slate-600 dark:text-slate-400">校對 Prompt (Proofread)</label>
                                                <button
                                                    onClick={async () => {
                                                        try {
                                                            const res = await axios.get(`${API_BASE}/default-proofread-prompt`);
                                                            if (res.data && res.data.prompt) {
                                                                setEditForm(prev => ({ ...prev, proofread_prompt: res.data.prompt }));
                                                            }
                                                        } catch (err) {
                                                            console.error("Failed to load default proofread prompt", err);
                                                        }
                                                    }}
                                                    className="text-[10px] bg-slate-200 hover:bg-slate-300 dark:bg-slate-700 dark:hover:bg-slate-600 text-slate-600 dark:text-slate-300 px-2 py-0.5 rounded transition-colors"
                                                    title="載入系統預設校對提示詞"
                                                >
                                                    載入預設
                                                </button>
                                            </div>
                                            <span className="text-xs text-slate-400">給予 LLM 的校對指示</span>
                                        </div>
                                        <textarea
                                            id={`proofread_prompt_${pl.id}`}
                                            value={editForm.proofread_prompt}
                                            onChange={e => setEditForm({ ...editForm, proofread_prompt: e.target.value })}
                                            rows={8}
                                            className="w-full bg-white dark:bg-[#0f172a] border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-[#3B82F6] outline-none resize-y min-h-[150px] font-mono leading-relaxed"
                                            placeholder="若留空，將使用預設校對指令..."
                                        />
                                    </div>
                                    <div className="space-y-1.5">
                                        <label htmlFor={`whisper_lang_${pl.id}`} className="text-sm font-medium text-slate-600 dark:text-slate-400">語言</label>
                                        <select
                                            id={`whisper_lang_${pl.id}`}
                                            value={editForm.whisper_lang}
                                            onChange={e => setEditForm({ ...editForm, whisper_lang: e.target.value })}
                                            className="w-full bg-white dark:bg-[#0f172a] border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-base focus:ring-2 focus:ring-[#3B82F6] outline-none"
                                        >
                                            <option value="auto">自動偵測 (auto)</option>
                                            <option value="Chinese">中文 (Chinese)</option>
                                            <option value="Burmese">緬甸語 (Burmese)</option>
                                            <option value="English">英文 (English)</option>
                                            <option value="Japanese">日文 (Japanese)</option>
                                        </select>
                                    </div>
                                    <div className="space-y-1.5">
                                        <label htmlFor={`whisper_model_${pl.id}`} className="text-sm font-medium text-slate-600 dark:text-slate-400">Whisper 模型</label>
                                        <select
                                            id={`whisper_model_${pl.id}`}
                                            value={editForm.whisper_model}
                                            onChange={e => setEditForm({ ...editForm, whisper_model: e.target.value })}
                                            className="w-full bg-white dark:bg-[#0f172a] border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-base focus:ring-2 focus:ring-[#3B82F6] outline-none"
                                        >
                                            <option value="large-v2">large-v2 (推薦)</option>
                                            <option value="large-v3">large-v3</option>
                                            <option value="medium">medium</option>
                                            <option value="small">small</option>
                                        </select>
                                    </div>
                                    <div className="space-y-1.5">
                                        <label htmlFor={`lecture_pdf_${pl.id}`} className="text-sm font-medium text-slate-600 dark:text-slate-400">講義 PDF 路徑</label>
                                        <input
                                            id={`lecture_pdf_${pl.id}`}
                                            type="text"
                                            value={editForm.lecture_pdf}
                                            onChange={e => setEditForm({ ...editForm, lecture_pdf: e.target.value })}
                                            className="w-full bg-white dark:bg-[#0f172a] border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-base focus:ring-2 focus:ring-[#3B82F6] outline-none"
                                            placeholder="/mnt/nas/..."
                                        />
                                    </div>
                                    <div className="space-y-1.5">
                                        <label htmlFor={`output_dir_${pl.id}`} className="text-sm font-medium text-slate-600 dark:text-slate-400">輸出目錄</label>
                                        <input
                                            id={`output_dir_${pl.id}`}
                                            type="text"
                                            value={editForm.output_dir}
                                            onChange={e => setEditForm({ ...editForm, output_dir: e.target.value })}
                                            className="w-full bg-white dark:bg-[#0f172a] border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-base focus:ring-2 focus:ring-[#3B82F6] outline-none"
                                            placeholder="/mnt/nas/..."
                                        />
                                    </div>
                                    <div className="space-y-1.5">
                                        <label htmlFor={`folder_prefix_${pl.id}`} className="text-sm font-medium text-slate-600 dark:text-slate-400">資料夾前綴 (例如 T097V)</label>
                                        <input
                                            id={`folder_prefix_${pl.id}`}
                                            type="text"
                                            value={editForm.folder_prefix}
                                            onChange={e => setEditForm({ ...editForm, folder_prefix: e.target.value })}
                                            className="w-full bg-white dark:bg-[#0f172a] border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-base focus:ring-2 focus:ring-[#3B82F6] outline-none"
                                            placeholder="T097V"
                                        />
                                    </div>
                                    <div className="space-y-1.5 flex items-center pt-6">
                                        <label className="flex items-center cursor-pointer space-x-3">
                                            <div className="relative">
                                                <input
                                                    type="checkbox"
                                                    className="sr-only"
                                                    checked={editForm.track}
                                                    onChange={e => setEditForm({ ...editForm, track: e.target.checked })}
                                                />
                                                <div className={`block w-10 h-6 rounded-full transition-colors ${editForm.track ? 'bg-emerald-500' : 'bg-slate-300 dark:bg-slate-600'}`}></div>
                                                <div className={`absolute left-1 top-1 bg-white w-4 h-4 rounded-full transition-transform ${editForm.track ? 'translate-x-4' : ''}`}></div>
                                            </div>
                                            <span className="text-sm font-semibold text-slate-600 dark:text-slate-400">啟用自動追蹤</span>
                                        </label>
                                    </div>
                                </div>
                            ) : (
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                                    <div className="bg-white dark:bg-[#161b22] rounded-lg p-3 border border-slate-100 dark:border-slate-800 col-span-2">
                                        <div className="text-xs text-slate-400 mb-1">Whisper Prompt</div>
                                        <div className="text-base line-clamp-2" title={pl.whisper_prompt}>{pl.whisper_prompt || '—'}</div>
                                    </div>
                                    <div className="bg-white dark:bg-[#161b22] rounded-lg p-3 border border-slate-100 dark:border-slate-800 col-span-2">
                                        <div className="text-xs text-slate-400 mb-1">校對 Prompt</div>
                                        <div className="text-base line-clamp-2" title={pl.proofread_prompt}>{pl.proofread_prompt || '—'}</div>
                                    </div>
                                    <div className="bg-white dark:bg-[#161b22] rounded-lg p-3 border border-slate-100 dark:border-slate-800">
                                        <div className="text-xs text-slate-400 mb-1">語言</div>
                                        <div className="text-base">{pl.whisper_lang}</div>
                                    </div>
                                    <div className="bg-white dark:bg-[#161b22] rounded-lg p-3 border border-slate-100 dark:border-slate-800">
                                        <div className="text-xs text-slate-400 mb-1">前綴</div>
                                        <div className="text-base font-mono">{pl.folder_prefix || 'T097V'}</div>
                                    </div>
                                    <div className="bg-white dark:bg-[#161b22] rounded-lg p-3 border border-slate-100 dark:border-slate-800 col-span-2">
                                        <div className="text-xs text-slate-400 mb-1">講義 PDF</div>
                                        <div className="text-base truncate" title={pl.lecture_pdf}>{pl.lecture_pdf || '—'}</div>
                                    </div>
                                    <div className="bg-white dark:bg-[#161b22] rounded-lg p-3 border border-slate-100 dark:border-slate-800 col-span-2">
                                        <div className="text-xs text-slate-400 mb-1">輸出目錄</div>
                                        <div className="text-base truncate" title={pl.output_dir}>{pl.output_dir || '—'}</div>
                                    </div>
                                    <div className="bg-white dark:bg-[#161b22] rounded-lg p-3 border border-slate-100 dark:border-slate-800">
                                        <div className="text-xs text-slate-400 mb-1">Whisper 模型</div>
                                        <div className="text-base font-mono">{pl.whisper_model}</div>
                                    </div>
                                    <div className="bg-white dark:bg-[#161b22] rounded-lg p-3 border border-slate-100 dark:border-slate-800">
                                        <div className="text-xs text-slate-400 mb-1">每輪集數</div>
                                        <div className="text-base font-mono text-center">{pl.batch_size}</div>
                                    </div>
                                    <div className="bg-white dark:bg-[#161b22] rounded-lg p-3 border border-slate-100 dark:border-slate-800">
                                        <div className="text-xs text-slate-400 mb-1">自動追蹤</div>
                                        <div className="text-base font-medium">
                                            {pl.track !== false ? (
                                                <span className="text-emerald-500">啟用</span>
                                            ) : (
                                                <span className="text-slate-400">關閉</span>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>
                    )}

                    {/* Video Table */}
                    {loadingEpisodes ? (
                        <div className="p-5 text-center text-sm text-slate-400 flex items-center justify-center space-x-2">
                            <Loader2 className="animate-spin" size={16} />
                            <span>載入影片列表...</span>
                        </div>
                    ) : episodes && episodes.length > 0 ? (
                        <div className="border-t border-slate-100 dark:border-slate-800">
                            <div className="overflow-x-auto max-h-80 overflow-y-auto">
                                <table className="w-full text-left text-sm whitespace-nowrap">
                                    <thead className="bg-slate-50 dark:bg-slate-800/80 sticky top-0 z-10 shadow-sm backdrop-blur-sm">
                                        <tr className="text-sm text-slate-500 dark:text-slate-400 border-b border-slate-200 dark:border-slate-700">
                                            <th className="px-5 py-3.5 font-medium w-16">
                                                <Hash size={14} className="inline mr-1" />
                                                集號
                                            </th>
                                            <th className="px-5 py-3.5 font-medium w-1/3 min-w-[200px]">影片名稱</th>
                                            <th className="px-5 py-3.5 font-medium text-center">進度</th>
                                            <th className="px-5 py-3.5 font-medium w-40 text-right">時間</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                                        {(episodes || [])
                                            .sort((a: EpisodeStatus, b: EpisodeStatus) => {
                                                const numA = parseInt((a.title || '').match(/(\d+)\s*$/)?.[1] || '0', 10);
                                                const numB = parseInt((b.title || '').match(/(\d+)\s*$/)?.[1] || '0', 10);
                                                return numA - numB;
                                            })
                                            .map((v: EpisodeStatus, idx: number) => (
                                                <tr key={v.video_id} className="hover:bg-slate-50 dark:hover:bg-slate-800/30 transition-colors">
                                                    <td className="px-5 py-4 text-slate-500 font-mono text-sm">{idx + 1}</td>
                                                    <td className="px-5 py-4">
                                                        <div className="flex flex-col">
                                                            <div className="flex items-center space-x-2.5">
                                                                <FileText size={16} className="text-[#3B82F6] flex-shrink-0" />
                                                                <span className="truncate flex-1 font-medium text-slate-700 dark:text-slate-200 text-[15px]" title={v.title}>{v.title}</span>
                                                            </div>
                                                            <div className="text-xs text-slate-400 mt-1 ml-6 font-mono">
                                                                {v.video_id}
                                                            </div>
                                                        </div>
                                                    </td>
                                                    <td className="px-5 py-4">
                                                        <div className="flex items-center justify-center space-x-3 bg-slate-50/50 dark:bg-[#161b22] rounded-xl py-2 px-4 shadow-sm border border-slate-100 dark:border-slate-800">
                                                            <StatusStep label="下載" done={v.download_done} onClick={() => handleRedo(v.video_id, 'download')} />
                                                            <span className="text-slate-200 dark:text-slate-700">|</span>
                                                            <StatusStep label="轉錄" done={v.whisper_done} onClick={() => handleRedo(v.video_id, 'whisper')} />
                                                            <span className="text-slate-200 dark:text-slate-700">|</span>
                                                            <StatusStep label="校對" done={v.proofread_done} onClick={() => handleRedo(v.video_id, 'proofread')} />
                                                            <span className="text-slate-200 dark:text-slate-700">|</span>
                                                            <StatusStep label="排版" done={v.report_done} onClick={() => handleRedo(v.video_id, 'report')} />
                                                        </div>
                                                    </td>
                                                    <td className="px-5 py-4 text-sm text-slate-500 font-mono whitespace-nowrap text-right">
                                                        {v.processed_at ? formatTime(v.processed_at) : '—'}
                                                    </td>
                                                </tr>
                                            ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    ) : (
                        <div className="border-t border-slate-100 dark:border-slate-800 p-5 text-center text-sm text-slate-400">
                            尚無已處理的影片
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

/* ─── Add Playlist Modal ────────────────────────────── */

function AddPlaylistModal({ onClose, onSave }: {
    onClose: () => void;
    onSave: (data: Record<string, unknown>) => void;
}) {
    const [form, setForm] = useState({
        id: `pl_${Date.now()}`,
        name: '',
        url: '',
        output_dir: '',
        whisper_model: 'large-v2',
        enabled: true,
        schedule: 'daily',
        whisper_lang: 'auto',
        whisper_prompt: '',
        proofread_prompt: '',
        lecture_pdf: '',
        batch_size: 5,
        folder_prefix: 'T097V',
        track: true,
    });

    const [detecting, setDetecting] = useState(false);
    const [urlInfo, setUrlInfo] = useState<UrlDetectResult | null>(null);

    useEffect(() => {
        axios.get(`${API_BASE}/default-proofread-prompt`)
            .then(res => {
                if (res.data && res.data.prompt) {
                    setForm(f => ({ ...f, proofread_prompt: res.data.prompt }));
                }
            })
            .catch(err => console.error("Failed to fetch default proofread prompt", err));
    }, []);

    const detectUrl = async (url: string) => {
        if (!url.includes('youtube.com') && !url.includes('youtu.be')) return;
        setDetecting(true);
        setUrlInfo(null);
        try {
            const res = await axios.post(`${API_BASE}/url/detect`, { url });
            setUrlInfo(res.data);
            // Auto fill name if empty
            if (res.data.title && !form.name) {
                setForm(f => ({ ...f, name: res.data.title }));
            }
        } catch {
            setUrlInfo(null);
        } finally {
            setDetecting(false);
        }
    };

    const handleUrlChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const url = e.target.value;
        setForm({ ...form, url });
        // Debounce detect
        if (url.length > 20) {
            const timer = setTimeout(() => detectUrl(url), 600);
            return () => clearTimeout(timer);
        }
    };

    const handleSubmit = () => {
        if (!form.name || !form.url) {
            alert('請填寫名稱和網址');
            return;
        }
        onSave(form);
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
            <div className="bg-white dark:bg-[#1c2128] rounded-2xl shadow-2xl w-full max-w-xl p-6 space-y-5 max-h-[90vh] overflow-y-auto">
                <h3 className="text-xl font-bold text-slate-800 dark:text-white border-b border-slate-200 dark:border-slate-700 pb-4">
                    新增播放清單
                </h3>

                <div className="space-y-4">
                    <div className="space-y-1.5">
                        <label htmlFor="new_playlist_name" className="text-sm font-medium text-slate-700 dark:text-slate-300">
                            清單名稱 <span className="text-slate-400 font-normal ml-1">(貼上網址後系統會自動偵測，亦可手動修改)</span> *
                        </label>
                        <input id="new_playlist_name" type="text" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })}
                            className="w-full bg-slate-50 dark:bg-[#0f172a] border border-slate-200 dark:border-slate-700 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-[#3B82F6] outline-none"
                            placeholder={detecting ? "正在自動抓取清單名稱..." : "例如: 淨空法師開示 第一輯"} />
                    </div>

                    <div className="space-y-1.5">
                        <label htmlFor="new_playlist_url" className="text-sm font-medium text-slate-700 dark:text-slate-300">YouTube 網址 *</label>
                        <div className="relative">
                            <input id="new_playlist_url" type="text" value={form.url} onChange={handleUrlChange}
                                className="w-full bg-slate-50 dark:bg-[#0f172a] border border-slate-200 dark:border-slate-700 rounded-lg px-4 py-2 pr-10 text-sm font-mono focus:ring-2 focus:ring-[#3B82F6] outline-none"
                                placeholder="https://youtube.com/playlist?list=..." />
                            {detecting && <Loader2 size={16} className="absolute right-3 top-1/2 -translate-y-1/2 text-blue-400 animate-spin" />}
                        </div>
                        {urlInfo && (
                            <div className={`flex items-center space-x-2 text-xs px-3 py-2 rounded-lg mt-1 ${urlInfo.type === 'playlist' ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400' : 'bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400'}`}>
                                {urlInfo.type === 'playlist' ? <List size={14} /> : <Film size={14} />}
                                <span>{urlInfo.type === 'playlist' ? `📋 播放清單 (${urlInfo.count} 集)` : `🎬 單一影片${urlInfo.title ? `: ${urlInfo.title}` : ''}`}</span>
                            </div>
                        )}
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-1.5 opacity-60">
                            <label htmlFor="new_playlist_output_dir" className="text-sm font-medium text-slate-700 dark:text-slate-300">輸出目錄 (自動鎖定)</label>
                            <input id="new_playlist_output_dir" type="text" value={form.output_dir} disabled
                                className="w-full bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-4 py-2 text-sm focus:ring-0 outline-none cursor-not-allowed"
                                placeholder="系統將依前綴自動產生路徑" />
                        </div>
                        <div className="space-y-1.5">
                            <label htmlFor="new_playlist_folder_prefix" className="text-sm font-medium text-slate-700 dark:text-slate-300">資料夾前綴 (例如 T097V) *</label>
                            <input id="new_playlist_folder_prefix" type="text" value={form.folder_prefix} onChange={e => setForm({ ...form, folder_prefix: e.target.value })}
                                className="w-full bg-slate-50 dark:bg-[#0f172a] border border-slate-200 dark:border-slate-700 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-[#3B82F6] outline-none"
                                placeholder="T097V" />
                        </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="space-y-1.5">
                            <label htmlFor="new_playlist_whisper_model" className="text-sm font-medium text-slate-700 dark:text-slate-300">Whisper 模型</label>
                            <select id="new_playlist_whisper_model" value={form.whisper_model} onChange={e => setForm({ ...form, whisper_model: e.target.value })}
                                className="w-full bg-slate-50 dark:bg-[#0f172a] border border-slate-200 dark:border-slate-700 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-[#3B82F6] outline-none">
                                <option value="large-v2">large-v2 (推薦)</option>
                                <option value="large-v3">large-v3</option>
                                <option value="medium">medium</option>
                                <option value="small">small</option>
                            </select>
                        </div>
                        <div className="space-y-1.5">
                            <label htmlFor="new_playlist_whisper_lang" className="text-sm font-medium text-slate-700 dark:text-slate-300">語言</label>
                            <select id="new_playlist_whisper_lang" value={form.whisper_lang} onChange={e => setForm({ ...form, whisper_lang: e.target.value })}
                                className="w-full bg-slate-50 dark:bg-[#0f172a] border border-slate-200 dark:border-slate-700 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-[#3B82F6] outline-none">
                                <option value="auto">自動偵測 (auto)</option>
                                <option value="Chinese">中文 (Chinese)</option>
                                <option value="English">英文 (English)</option>
                            </select>
                        </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="space-y-1.5">
                            <label htmlFor="new_playlist_batch_size" className="text-sm font-medium text-slate-700 dark:text-slate-300">每輪處理集數</label>
                            <input id="new_playlist_batch_size" type="number" min={1} max={50} value={form.batch_size}
                                onChange={e => setForm({ ...form, batch_size: parseInt(e.target.value) || 5 })}
                                className="w-full bg-slate-50 dark:bg-[#0f172a] border border-slate-200 dark:border-slate-700 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-[#3B82F6] outline-none" />
                        </div>
                        <div className="space-y-1.5 flex items-center pt-6">
                            <label className="flex items-center cursor-pointer space-x-3">
                                <div className="relative">
                                    <input
                                        type="checkbox"
                                        className="sr-only"
                                        checked={form.track}
                                        onChange={e => setForm({ ...form, track: e.target.checked })}
                                    />
                                    <div className={`block w-10 h-6 rounded-full transition-colors ${form.track ? 'bg-emerald-500' : 'bg-slate-300 dark:bg-slate-600'}`}></div>
                                    <div className={`absolute left-1 top-1 bg-white w-4 h-4 rounded-full transition-transform ${form.track ? 'translate-x-4' : ''}`}></div>
                                </div>
                                <span className="text-sm font-medium text-slate-700 dark:text-slate-300">啟用影片追蹤 (Auto Tracking)</span>
                            </label>
                        </div>
                    </div>

                    <div className="space-y-1.5">
                        <label htmlFor="new_playlist_lecture_pdf" className="text-sm font-medium text-slate-700 dark:text-slate-300">講義 PDF 路徑 (選填)</label>
                        <input id="new_playlist_lecture_pdf" type="text" value={form.lecture_pdf} onChange={e => setForm({ ...form, lecture_pdf: e.target.value })}
                            className="w-full bg-slate-50 dark:bg-[#0f172a] border border-slate-200 dark:border-slate-700 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-[#3B82F6] outline-none"
                            placeholder="系統會自動偵測，若需手動指定請輸入路徑" />
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="space-y-1.5">
                            <label htmlFor="new_playlist_whisper_prompt" className="text-sm font-medium text-slate-700 dark:text-slate-300">Whisper 提示詞 (Prompt)</label>
                            <textarea id="new_playlist_whisper_prompt" value={form.whisper_prompt} onChange={e => setForm({ ...form, whisper_prompt: e.target.value })}
                                rows={3}
                                className="w-full bg-slate-50 dark:bg-[#0f172a] border border-slate-200 dark:border-slate-700 rounded-lg px-4 py-2 text-base focus:ring-2 focus:ring-[#3B82F6] outline-none resize-none font-mono"
                                placeholder="引導 Whisper 的提示詞..." />
                        </div>
                        <div className="space-y-1.5 md:col-span-2">
                            <div className="flex items-center justify-between">
                                <label htmlFor="new_playlist_proofread_prompt" className="text-sm font-medium text-slate-700 dark:text-slate-300">校對提示詞 (Proofread Prompt)</label>
                                <span className="text-xs text-slate-400">預設已載入系統通用 Prompt，可針對此清單修改</span>
                            </div>
                            <textarea id="new_playlist_proofread_prompt" value={form.proofread_prompt} onChange={e => setForm({ ...form, proofread_prompt: e.target.value })}
                                rows={8}
                                className="w-full bg-slate-50 dark:bg-[#0f172a] border border-slate-200 dark:border-slate-700 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-[#3B82F6] outline-none resize-y font-mono leading-relaxed"
                                placeholder="引導 LLM 的校對提示指示..." />
                        </div>
                    </div>
                </div>

                <div className="flex justify-end space-x-3 pt-4 border-t border-slate-200 dark:border-slate-700">
                    <button onClick={onClose} className="px-4 py-2 rounded-lg text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 font-medium transition-colors">取消</button>
                    <button onClick={handleSubmit} className="px-5 py-2 rounded-lg bg-[#3B82F6] hover:bg-blue-600 text-white font-medium shadow-sm transition-colors">新增清單</button>
                </div>
            </div>
        </div>
    );
}

/* ─── Main Component ────────────────────────────────── */

export default function PlaylistTaskManager({ data, onRefresh }: {
    data: DashboardData | null;
    onRefresh: () => void;
}) {
    const [expandedId, setExpandedId] = useState<string | null>(null);
    const [isFullScreen, setIsFullScreen] = useState(false);
    const [showAddModal, setShowAddModal] = useState(false);

    const handleControl = useCallback(async (id: string, action: string) => {
        try {
            await axios.post(`${API_BASE}/playlists/${id}/control`, { action });
            onRefresh();
        } catch (e) {
            console.error('Control failed', e);
        }
    }, [onRefresh]);

    const handleUpdate = useCallback(async (id: string, updates: Record<string, unknown>) => {
        try {
            await axios.put(`${API_BASE}/playlists/${id}`, updates);
            onRefresh();
        } catch (e) {
            console.error('Update failed', e);
        }
    }, [onRefresh]);

    const handleDelete = useCallback(async (id: string) => {
        if (!confirm('確定要刪除此清單嗎？')) return;
        try {
            await axios.delete(`${API_BASE}/playlists/${id}`);
            onRefresh();
        } catch (e) {
            console.error('Delete failed', e);
        }
    }, [onRefresh]);

    const handleAddPlaylist = useCallback(async (formData: Record<string, unknown>) => {
        try {
            await axios.post(`${API_BASE}/playlists`, formData);
            setShowAddModal(false);
            onRefresh();
        } catch (e) {
            console.error('Create failed', e);
            alert('新增清單失敗');
        }
    }, [onRefresh]);

    const handleTriggerWhisper = useCallback(async () => {
        try {
            const res = await axios.post(`${API_BASE}/task`, { action: 'whisper', target: 'auto' });
            if (res.data.status === 'busy') {
                alert('Whisper 任務正在執行中，請稍後再試');
            }
        } catch (e) {
            console.error('Trigger whisper failed', e);
        }
    }, []);

    const handleTriggerProofread = useCallback(async () => {
        try {
            await axios.post(`${API_BASE}/task`, { action: 'proofread', target: 'auto' });
        } catch (e) {
            console.error('Trigger proofread failed', e);
        }
    }, []);

    if (!data) {
        return (
            <div className="flex items-center justify-center py-16 text-slate-400">
                <Loader2 size={20} className="animate-spin mr-2" />
                <span>正在載入任務資料...</span>
            </div>
        );
    }

    const { playlists, global_stats } = data;

    return (
        <div className="w-full xl:px-4 mx-auto space-y-6">
            {/* Top Action Bar */}
            <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                <div>
                    <h2 className="text-xl font-bold text-slate-800 dark:text-white">播放清單任務管理</h2>
                    <p className="text-sm text-slate-500 mt-1">
                        共 {global_stats.total_playlists} 個清單 · {global_stats.active_playlists} 個啟用中 · {global_stats.total_videos} 集已處理
                    </p>
                </div>
                <div className="flex items-center space-x-3">
                    <button onClick={handleTriggerProofread}
                        className="bg-[#3B82F6] hover:bg-[#2563EB] text-white rounded-xl px-4 py-2.5 font-medium flex items-center space-x-2 transition-colors text-sm">
                        <Play size={16} />
                        <span>啟動校對</span>
                    </button>
                    <button onClick={handleTriggerWhisper}
                        className="bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 rounded-xl px-4 py-2.5 font-medium flex items-center space-x-2 transition-colors text-sm">
                        <CircleDot size={16} />
                        <span>執行 Whisper</span>
                    </button>
                    <button onClick={() => setShowAddModal(true)}
                        className="bg-[#1E293B] hover:bg-slate-700 text-white rounded-xl px-4 py-2.5 font-medium flex items-center space-x-2 transition-colors text-sm">
                        <Plus size={16} />
                        <span>新增清單</span>
                    </button>
                </div>
            </div>

            {/* Playlist Cards */}
            <div className="grid grid-cols-1 gap-4">
                {playlists.map((pl) => (
                    <PlaylistCard
                        key={pl.id}
                        pl={pl}
                        isExpanded={expandedId === pl.id}
                        isFullScreen={expandedId === pl.id && isFullScreen}
                        onToggleFullScreen={() => setIsFullScreen(!isFullScreen)}
                        onToggle={() => {
                            if (expandedId === pl.id) {
                                setExpandedId(null);
                                setIsFullScreen(false);
                            } else {
                                setExpandedId(pl.id);
                            }
                        }}
                        onControl={(action) => handleControl(pl.id, action)}
                        onUpdate={handleUpdate}
                        onDelete={handleDelete}
                    />
                ))}
            </div>

            {playlists.length === 0 && (
                <div className="text-center py-16 text-slate-400">
                    <ListVideo size={48} className="mx-auto mb-4 opacity-40" />
                    <p className="text-lg">尚未新增任何播放清單</p>
                    <p className="text-sm mt-1">點擊「新增清單」開始管理 YouTube 播放清單</p>
                </div>
            )}

            {/* Add Playlist Modal */}
            {showAddModal && (
                <AddPlaylistModal
                    onClose={() => setShowAddModal(false)}
                    onSave={handleAddPlaylist}
                />
            )}
        </div>
    );
}
