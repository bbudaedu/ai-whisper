import { useState, useEffect } from 'react';
import axios from 'axios';
import { Save, AlertCircle, FileText, Bot, Languages, Mail, Database } from 'lucide-react';

const API_BASE = `http://${window.location.hostname}:8000/api`;

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
    const [saving, setSaving] = useState(false);
    const [saveStatus, setSaveStatus] = useState<string | null>(null);

    useEffect(() => {
        fetchConfig();
    }, []);

    const fetchConfig = async () => {
        try {
            const res = await axios.get(`${API_BASE}/config`);
            setConfig(res.data);
        } catch (e) {
            console.error('Failed to fetch config', e);
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

    return (
        <div className="bg-white dark:bg-[#1c2128] rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden p-6 md:p-8 max-w-4xl mx-auto space-y-8">

            <div className="flex justify-between items-center border-b border-slate-100 dark:border-slate-800 pb-4">
                <h2 className="text-xl font-bold flex items-center space-x-2">
                    <span>參數設定 (Configuration)</span>
                </h2>
                <button
                    onClick={handleSave}
                    disabled={saving}
                    className="bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-400 text-white rounded-xl px-5 py-2.5 font-medium flex items-center space-x-2 transition-colors focus:ring-4 focus:ring-indigo-500/20"
                >
                    <Save size={18} />
                    <span>{saving ? '儲存中...' : '儲存設定'}</span>
                </button>
            </div>

            {saveStatus === 'success' && (
                <div className="bg-green-50 dark:bg-green-500/10 text-green-700 dark:text-green-400 p-4 rounded-xl flex items-center space-x-2">
                    <AlertCircle size={18} />
                    <span>設定已成功儲存！自動由所有背景腳本生效。</span>
                </div>
            )}

            {/* YouTube & 系統儲存區塊 */}
            <section className="space-y-4">
                <h3 className="text-lg font-semibold flex items-center space-x-2 text-indigo-600 dark:text-indigo-400">
                    <Database size={20} />
                    <span>YouTube 與儲存路徑</span>
                </h3>

                <div className="grid grid-cols-1 gap-6">
                    <div className="space-y-1.5">
                        <label className="text-sm font-medium text-slate-700 dark:text-slate-300">YouTube 播放清單網址 (Playlist URL)</label>
                        <input
                            type="text"
                            name="playlist_url"
                            value={config.playlist_url}
                            onChange={handleChange}
                            className="w-full bg-slate-50 dark:bg-[#21262d] border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-2.5 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                        />
                    </div>
                    <div className="space-y-1.5">
                        <label className="text-sm font-medium text-slate-700 dark:text-slate-300">NAS 輸出主目錄 (NAS Output Base)</label>
                        <input
                            type="text"
                            name="nas_output_base"
                            value={config.nas_output_base}
                            onChange={handleChange}
                            className="w-full bg-slate-50 dark:bg-[#21262d] border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-2.5 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                        />
                    </div>
                </div>
            </section>

            <hr className="border-slate-100 dark:border-slate-800" />

            {/* Whisper 區塊 */}
            <section className="space-y-4">
                <h3 className="text-lg font-semibold flex items-center space-x-2 text-indigo-600 dark:text-indigo-400">
                    <Bot size={20} />
                    <span>Whisper 語音辨識設定</span>
                </h3>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="space-y-1.5">
                        <label className="text-sm font-medium text-slate-700 dark:text-slate-300">Whisper 模型 (Model)</label>
                        <select name="whisper_model" value={config.whisper_model} onChange={handleChange} className="w-full bg-slate-50 dark:bg-[#21262d] border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-2.5 focus:ring-2 focus:ring-indigo-500 focus:outline-none">
                            <option value="large-v2">large-v2 (推薦精度最高)</option>
                            <option value="large-v3">large-v3</option>
                            <option value="medium">medium</option>
                            <option value="small">small</option>
                        </select>
                    </div>
                    <div className="space-y-1.5">
                        <label className="text-sm font-medium text-slate-700 dark:text-slate-300">來源語言 (Language)</label>
                        <div className="flex items-center absolute"></div>
                        <select name="whisper_lang" value={config.whisper_lang} onChange={handleChange} className="w-full bg-slate-50 dark:bg-[#21262d] border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-2.5 focus:ring-2 focus:ring-indigo-500 focus:outline-none">
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
                        className="w-full bg-slate-50 dark:bg-[#21262d] border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-2.5 focus:ring-2 focus:ring-indigo-500 focus:outline-none resize-none"
                        placeholder="請輸入 Whisper 起始 Prompt..."
                    />
                </div>
            </section>

            <hr className="border-slate-100 dark:border-slate-800" />

            {/* Gemini 校對區塊 */}
            <section className="space-y-4">
                <h3 className="text-lg font-semibold flex items-center space-x-2 text-indigo-600 dark:text-indigo-400">
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
                            className="w-full bg-slate-50 dark:bg-[#21262d] border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-2.5 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
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
                            className="w-full bg-slate-50 dark:bg-[#21262d] border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-2.5 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                        />
                    </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <div className="space-y-1.5">
                        <label className="text-sm font-medium text-slate-700 dark:text-slate-300">Gemini 模型選擇</label>
                        <select name="proofread_model" value={config.proofread_model} onChange={handleChange} className="w-full bg-slate-50 dark:bg-[#21262d] border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-2.5 focus:ring-2 focus:ring-indigo-500 focus:outline-none">
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
                            className="w-full bg-slate-50 dark:bg-[#21262d] border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-2.5 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
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
                            className="w-full bg-slate-50 dark:bg-[#21262d] border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-2.5 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
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
                            className="w-full bg-slate-50 dark:bg-[#21262d] border border-slate-200 dark:border-slate-700 rounded-xl pl-10 pr-4 py-2.5 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                            placeholder="/mnt/nas/Whisper_auto_rum/T097V/CHxxx.pdf"
                        />
                    </div>
                </div>
            </section>

            <hr className="border-slate-100 dark:border-slate-800" />

            {/* 通知區塊 */}
            <section className="space-y-4">
                <h3 className="text-lg font-semibold flex items-center space-x-2 text-indigo-600 dark:text-indigo-400">
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
                        className="w-full bg-slate-50 dark:bg-[#21262d] border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-2.5 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                        placeholder="jacky@example.com, test@example.com"
                    />
                </div>
            </section>

        </div>
    );
}
