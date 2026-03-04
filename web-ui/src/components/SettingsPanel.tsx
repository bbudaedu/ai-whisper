import { useState, useEffect } from 'react';
import axios from 'axios';
import { Save, AlertCircle, FileText, Bot, Languages, Mail, Database, Plus, Trash2, Edit2, CheckCircle2 } from 'lucide-react';

const API_BASE = `http://${window.location.hostname}:8002/api`;

interface Playlist {
    id: string;
    name: string;
    url: string;
    output_dir: string;
    whisper_model: string;
    enabled: boolean;
    schedule: string;
}

export default function SettingsPanel() {
    const [config, setConfig] = useState({
        playlist_url: '',
        nas_output_base: '',
        api_base_url: '',
        api_key: '',
        proofread_model: 'gemini-3-flash',
        proofread_chunk_size: 100,
        punct_chunk_size: 120,
        lecture_pdf: '',
        whisper_model: 'large-v2',
        whisper_lang: 'Chinese',
        whisper_prompt: '',
        email_to: ''
    });

    // Playlists state
    const [playlists, setPlaylists] = useState<Playlist[]>([]);
    const [showPlaylistModal, setShowPlaylistModal] = useState(false);
    const [editingPlaylist, setEditingPlaylist] = useState<Playlist | null>(null);
    const [playlistForm, setPlaylistForm] = useState<Partial<Playlist>>({});

    const [saving, setSaving] = useState(false);
    const [saveStatus, setSaveStatus] = useState<string | null>(null);

    useEffect(() => {
        fetchConfig();
        fetchPlaylists();
    }, []);

    const fetchConfig = async () => {
        try {
            const res = await axios.get(`${API_BASE}/config`);
            setConfig(res.data);
        } catch (e) {
            console.error('Failed to fetch config', e);
        }
    };

    const fetchPlaylists = async () => {
        try {
            const res = await axios.get(`${API_BASE}/playlists`);
            setPlaylists(res.data);
        } catch (e) {
            console.error('Failed to fetch playlists', e);
        }
    };

    const handleSave = async () => {
        setSaving(true);
        setSaveStatus(null);
        try {
            await axios.post(`${API_BASE}/config`, config);
            setSaveStatus('success');
            setTimeout(() => setSaveStatus(null), 3000);
        } catch (e) {
            console.error('Save failed', e);
            setSaveStatus('error');
        } finally {
            setSaving(false);
        }
    };

    const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
        const { name, value } = e.target;
        setConfig(prev => ({ ...prev, [name]: value }));
    };

    // Playlist Handlers
    const handlePlaylistToggle = async (id: string, currentStatus: boolean) => {
        try {
            await axios.put(`${API_BASE}/playlists/${id}`, { enabled: !currentStatus });
            fetchPlaylists();
        } catch (e) {
            console.error('Failed to toggle playlist', e);
        }
    };

    const handlePlaylistDelete = async (id: string) => {
        if (!confirm('確定要刪除此清單嗎？')) return;
        try {
            await axios.delete(`${API_BASE}/playlists/${id}`);
            fetchPlaylists();
        } catch (e) {
            console.error('Failed to delete playlist', e);
        }
    };

    const openPlaylistModal = (playlist: Playlist | null = null) => {
        if (playlist) {
            setEditingPlaylist(playlist);
            setPlaylistForm(playlist);
        } else {
            setEditingPlaylist(null);
            setPlaylistForm({
                id: `pl_${Date.now()}`,
                name: '',
                url: '',
                output_dir: '',
                whisper_model: 'large-v3',
                enabled: true,
                schedule: 'daily'
            });
        }
        setShowPlaylistModal(true);
    };

    const savePlaylist = async () => {
        if (!playlistForm.name || !playlistForm.url) {
            alert("請填寫名稱和網址");
            return;
        }

        try {
            if (editingPlaylist) {
                await axios.put(`${API_BASE}/playlists/${playlistForm.id}`, playlistForm);
            } else {
                await axios.post(`${API_BASE}/playlists`, playlistForm);
            }
            setShowPlaylistModal(false);
            fetchPlaylists();
        } catch (e) {
            console.error('Failed to save playlist', e);
            alert("存檔失敗");
        }
    };

    return (
        <div className="bg-[#F8FAFC] dark:bg-[#0f172a] rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden p-6 md:p-8 max-w-5xl mx-auto space-y-8 font-['Fira_Sans',_sans-serif]">

            <div className="flex justify-between items-center border-b border-slate-200 dark:border-slate-800 pb-4">
                <h2 className="text-2xl font-bold flex items-center space-x-2 text-[#1E293B] dark:text-slate-100">
                    <span>參數與播放清單設定</span>
                </h2>
                <button
                    onClick={handleSave}
                    disabled={saving}
                    className="bg-[#3B82F6] hover:bg-blue-600 disabled:bg-blue-300 text-white rounded-xl px-5 py-2.5 font-medium flex items-center space-x-2 transition-colors focus:ring-4 focus:ring-blue-500/20"
                >
                    <Save size={18} />
                    <span>{saving ? '儲存中...' : '儲存全域設定'}</span>
                </button>
            </div>

            {saveStatus === 'success' && (
                <div className="bg-green-50 dark:bg-green-500/10 text-green-700 dark:text-green-400 p-4 rounded-xl flex items-center space-x-2">
                    <CheckCircle2 size={18} />
                    <span>設定已成功儲存！</span>
                </div>
            )}

            {/* Playlist Manager Dashboard (New) */}
            <section className="space-y-4">
                <div className="flex justify-between items-center">
                    <h3 className="text-xl font-semibold flex items-center space-x-2 text-[#3B82F6]">
                        <Database size={22} />
                        <span>多播放清單管理 (Multi-Playlist Dashboard)</span>
                    </h3>
                    <button
                        onClick={() => openPlaylistModal()}
                        className="bg-[#1E293B] hover:bg-slate-700 text-white rounded-lg px-4 py-2 text-sm font-medium flex items-center space-x-1 transition-colors"
                    >
                        <Plus size={16} />
                        <span>新增清單</span>
                    </button>
                </div>

                <div className="overflow-x-auto border border-slate-200 dark:border-slate-700 rounded-xl bg-white dark:bg-[#1E293B] shadow-sm">
                    <table className="w-full text-left text-sm whitespace-nowrap">
                        <thead className="bg-[#F8FAFC] dark:bg-slate-800 text-slate-500 dark:text-slate-400 font-['Fira_Code',_monospace] border-b border-slate-200 dark:border-slate-700">
                            <tr>
                                <th className="px-6 py-4 font-medium">名稱</th>
                                <th className="px-6 py-4 font-medium">網址 (URL)</th>
                                <th className="px-6 py-4 font-medium">Model</th>
                                <th className="px-6 py-4 font-medium">狀態</th>
                                <th className="px-6 py-4 font-medium text-right">操作</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 dark:divide-slate-800 text-slate-700 dark:text-slate-300">
                            {playlists.length === 0 ? (
                                <tr>
                                    <td colSpan={5} className="px-6 py-8 text-center text-slate-400 italic">
                                        尚無自訂播放清單，系統將使用下方預設網址 (若有)。
                                    </td>
                                </tr>
                            ) : (
                                playlists.map(pl => (
                                    <tr key={pl.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors">
                                        <td className="px-6 py-4 font-medium">{pl.name}</td>
                                        <td className="px-6 py-4 font-['Fira_Code',_monospace] text-xs text-slate-500 truncate max-w-[200px]" title={pl.url}>
                                            {pl.url}
                                        </td>
                                        <td className="px-6 py-4">
                                            <span className="bg-[#60A5FA]/10 text-[#3B82F6] px-2.5 py-1 rounded-md text-xs font-semibold">
                                                {pl.whisper_model}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4">
                                            <button
                                                onClick={() => handlePlaylistToggle(pl.id, pl.enabled)}
                                                className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${pl.enabled ? 'bg-green-500' : 'bg-slate-300 dark:bg-slate-600'}`}
                                            >
                                                <span className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform ${pl.enabled ? 'translate-x-4' : 'translate-x-1'}`} />
                                            </button>
                                        </td>
                                        <td className="px-6 py-4 text-right space-x-2">
                                            <button onClick={() => openPlaylistModal(pl)} className="text-[#60A5FA] hover:text-[#3B82F6] p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors">
                                                <Edit2 size={16} />
                                            </button>
                                            <button onClick={() => handlePlaylistDelete(pl.id)} className="text-[#F97316] hover:text-red-600 p-1.5 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors">
                                                <Trash2 size={16} />
                                            </button>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </section>

            {/* Playlist Modal */}
            {showPlaylistModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 font-['Fira_Sans',_sans-serif]">
                    <div className="bg-white dark:bg-[#1E293B] rounded-2xl shadow-xl w-full max-w-lg p-6 space-y-6">
                        <h3 className="text-xl font-bold text-slate-800 dark:text-white border-b pb-4">
                            {editingPlaylist ? '編輯播放清單' : '新增播放清單'}
                        </h3>

                        <div className="space-y-4">
                            <div className="space-y-1.5">
                                <label className="text-sm font-medium text-slate-700 dark:text-slate-300">清單名稱 *</label>
                                <input type="text" value={playlistForm.name || ''} onChange={e => setPlaylistForm({ ...playlistForm, name: e.target.value })} className="w-full bg-slate-50 dark:bg-[#0f172a] border border-slate-200 dark:border-slate-700 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-[#3B82F6] outline-none" placeholder="例如: 淨空法師開示" />
                            </div>

                            <div className="space-y-1.5">
                                <label className="text-sm font-medium text-slate-700 dark:text-slate-300">YouTube 網址 (URL) *</label>
                                <input type="text" value={playlistForm.url || ''} onChange={e => setPlaylistForm({ ...playlistForm, url: e.target.value })} className="w-full bg-slate-50 dark:bg-[#0f172a] border border-slate-200 dark:border-slate-700 rounded-lg px-4 py-2 text-sm font-['Fira_Code'] focus:ring-2 focus:ring-[#3B82F6] outline-none" placeholder="https://youtube.com/playlist?list=..." />
                            </div>

                            <div className="space-y-1.5">
                                <label className="text-sm font-medium text-slate-700 dark:text-slate-300">專屬輸出 NAS 目錄 (選填)</label>
                                <input type="text" value={playlistForm.output_dir || ''} onChange={e => setPlaylistForm({ ...playlistForm, output_dir: e.target.value })} className="w-full bg-slate-50 dark:bg-[#0f172a] border border-slate-200 dark:border-slate-700 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-[#3B82F6] outline-none" placeholder="若留空則使用全域設定" />
                            </div>

                            <div className="space-y-1.5">
                                <label className="text-sm font-medium text-slate-700 dark:text-slate-300">Whisper 優先模型</label>
                                <select value={playlistForm.whisper_model || 'large-v3'} onChange={e => setPlaylistForm({ ...playlistForm, whisper_model: e.target.value })} className="w-full bg-slate-50 dark:bg-[#0f172a] border border-slate-200 dark:border-slate-700 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-[#3B82F6] outline-none">
                                    <option value="large-v2">large-v2 (推薦精度最高)</option>
                                    <option value="large-v3">large-v3</option>
                                    <option value="medium">medium</option>
                                    <option value="small">small</option>
                                </select>
                            </div>
                        </div>

                        <div className="flex justify-end space-x-3 pt-4 border-t">
                            <button onClick={() => setShowPlaylistModal(false)} className="px-4 py-2 rounded-lg text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 font-medium transition-colors">取消</button>
                            <button onClick={savePlaylist} className="px-4 py-2 rounded-lg bg-[#3B82F6] hover:bg-blue-600 text-white font-medium shadow-sm transition-colors">儲存清單</button>
                        </div>
                    </div>
                </div>
            )}

            <hr className="border-slate-200 dark:border-slate-800 my-8" />

            {/* Global Settings Block (Legacy config.json) */}
            <section className="space-y-4 opacity-75">
                <h3 className="text-lg font-semibold flex items-center space-x-2 text-slate-500">
                    <Database size={20} />
                    <span>預設/全域路徑設定 (若播放清單未指定時使用)</span>
                </h3>

                <div className="grid grid-cols-1 gap-6">
                    <div className="space-y-1.5">
                        <label className="text-sm font-medium text-slate-700 dark:text-slate-300">NAS 預設輸出主目錄</label>
                        <input
                            type="text"
                            name="nas_output_base"
                            value={config.nas_output_base}
                            onChange={handleChange}
                            className="w-full bg-slate-50 dark:bg-[#1E293B] border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-2.5 focus:ring-2 focus:ring-[#3B82F6] focus:outline-none"
                        />
                    </div>
                </div>
            </section>

            {/* Whisper 區塊 */}
            <section className="space-y-4 pt-4 border-t border-slate-200 dark:border-slate-800">
                <h3 className="text-lg font-semibold flex items-center space-x-2 text-[#3B82F6]">
                    <Bot size={20} />
                    <span>Whisper 進階設定 (Global)</span>
                </h3>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="space-y-1.5">
                        <label className="text-sm font-medium text-slate-700 dark:text-slate-300">來源語言 (Language)</label>
                        <div className="flex items-center absolute"></div>
                        <select name="whisper_lang" value={config.whisper_lang} onChange={handleChange} className="w-full bg-slate-50 dark:bg-[#1E293B] border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-2.5 focus:ring-2 focus:ring-[#3B82F6] focus:outline-none">
                            <option value="Chinese">中文 (Chinese)</option>
                            <option value="English">英文 (English)</option>
                        </select>
                    </div>
                </div>

                <div className="space-y-1.5">
                    <label className="text-sm font-medium text-slate-700 dark:text-slate-300 text-slate-700 dark:text-slate-300">自訂 Prompt (Initial Prompt)</label>
                    <p className="text-xs text-slate-500 dark:text-slate-400 mb-2">引導 Whisper 的專有名詞與斷句風格。範例：「佛教公案選集 不要標點符號」</p>
                    <textarea
                        name="whisper_prompt"
                        value={config.whisper_prompt}
                        onChange={handleChange}
                        rows={2}
                        className="w-full bg-slate-50 dark:bg-[#1E293B] border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-2.5 focus:ring-2 focus:ring-[#3B82F6] focus:outline-none resize-none"
                        placeholder="請輸入 Whisper 起始 Prompt..."
                    />
                </div>
            </section>

            {/* Gemini 校對區塊 */}
            <section className="space-y-4 pt-4 border-t border-slate-200 dark:border-slate-800">
                <h3 className="text-lg font-semibold flex items-center space-x-2 text-[#3B82F6]">
                    <Languages size={20} />
                    <span>Gemini AI 校對設定</span>
                </h3>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="space-y-1.5">
                        <label className="text-sm font-medium text-slate-700 dark:text-slate-300">API 伺服器網址 (Base URL)</label>
                        <input
                            type="text"
                            name="api_base_url"
                            value={config.api_base_url}
                            onChange={handleChange}
                            className="w-full bg-slate-50 dark:bg-[#1E293B] border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-2.5 focus:ring-2 focus:ring-[#3B82F6] focus:outline-none"
                            placeholder="http://192.168.100.201:8045/v1/chat/completions"
                        />
                    </div>
                    <div className="space-y-1.5">
                        <label className="text-sm font-medium text-slate-700 dark:text-slate-300">API 金鑰 (API Key)</label>
                        <input
                            type="password"
                            name="api_key"
                            value={config.api_key}
                            onChange={handleChange}
                            className="w-full bg-slate-50 dark:bg-[#1E293B] border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-2.5 focus:ring-2 focus:ring-[#3B82F6] focus:outline-none"
                        />
                    </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <div className="space-y-1.5">
                        <label className="text-sm font-medium text-slate-700 dark:text-slate-300">Gemini 模型選擇</label>
                        <select name="proofread_model" value={config.proofread_model} onChange={handleChange} className="w-full bg-slate-50 dark:bg-[#1E293B] border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-2.5 focus:ring-2 focus:ring-[#3B82F6] focus:outline-none">
                            <option value="gemini-3-flash">Gemini 3 Flash (快速)</option>
                            <option value="gemini-3-pro">Gemini 3 Pro (高階推理)</option>
                            <option value="gemini-3-pro-low">Gemini 3 Pro Low (低配版)</option>
                        </select>
                    </div>
                    <div className="space-y-1.5">
                        <label className="text-sm font-medium text-slate-700 dark:text-slate-300 flex justify-between">
                            <span>校對批次量</span>
                            <span className="text-xs text-slate-400">行/次</span>
                        </label>
                        <input
                            type="number"
                            name="proofread_chunk_size"
                            value={config.proofread_chunk_size}
                            onChange={handleChange}
                            className="w-full bg-slate-50 dark:bg-[#1E293B] border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-2.5 focus:ring-2 focus:ring-[#3B82F6] focus:outline-none"
                        />
                    </div>
                    <div className="space-y-1.5">
                        <label className="text-sm font-medium text-slate-700 dark:text-slate-300 flex justify-between">
                            <span>排版批次量</span>
                            <span className="text-xs text-slate-400">句/次</span>
                        </label>
                        <input
                            type="number"
                            name="punct_chunk_size"
                            value={config.punct_chunk_size}
                            onChange={handleChange}
                            className="w-full bg-slate-50 dark:bg-[#1E293B] border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-2.5 focus:ring-2 focus:ring-[#3B82F6] focus:outline-none"
                        />
                    </div>
                </div>

                <div className="space-y-1.5">
                    <label className="text-sm font-medium text-slate-700 dark:text-slate-300">上課講義 PDF 路徑 (NAS 絕對路徑)</label>
                    <div className="relative">
                        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                            <FileText size={16} className="text-slate-400" />
                        </div>
                        <input
                            type="text"
                            name="lecture_pdf"
                            value={config.lecture_pdf}
                            onChange={handleChange}
                            className="w-full bg-slate-50 dark:bg-[#1E293B] border border-slate-200 dark:border-slate-700 rounded-xl pl-10 pr-4 py-2.5 focus:ring-2 focus:ring-[#3B82F6] focus:outline-none"
                            placeholder="/mnt/nas/Whisper_auto_rum/T097V/CHxxx.pdf"
                        />
                    </div>
                </div>
            </section>

            {/* 通知區塊 */}
            <section className="space-y-4 pt-4 border-t border-slate-200 dark:border-slate-800">
                <h3 className="text-lg font-semibold flex items-center space-x-2 text-[#3B82F6]">
                    <Mail size={20} />
                    <span>Email 通知設定</span>
                </h3>

                <div className="space-y-1.5">
                    <label className="text-sm font-medium text-slate-700 dark:text-slate-300">收件人 Email (可用逗號分隔多人)</label>
                    <input
                        type="text"
                        name="email_to"
                        value={config.email_to}
                        onChange={handleChange}
                        className="w-full bg-slate-50 dark:bg-[#1E293B] border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-2.5 focus:ring-2 focus:ring-[#3B82F6] focus:outline-none"
                        placeholder="jacky@example.com, test@example.com"
                    />
                </div>
            </section>

        </div>
    );
}
