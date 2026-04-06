import { useState, useEffect } from 'react';
import axios from 'axios';
import { Save, FileText, Languages, Mail, Database, CheckCircle2 } from 'lucide-react';

const API_BASE = `http://${window.location.hostname}:8002/api`;


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
        <div className="bg-[#F8FAFC] dark:bg-[#0f172a] rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden p-6 md:p-8 w-full mx-auto space-y-8 font-['Fira_Sans',_sans-serif]">

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



            {/* Global Settings Block (Legacy config.json) */}
            <section className="space-y-4 opacity-75">
                <h3 className="text-lg font-semibold flex items-center space-x-2 text-slate-500">
                    <Database size={20} />
                    <span>預設/全域路徑設定 (若播放清單未指定時使用)</span>
                </h3>

                <div className="grid grid-cols-1 gap-6">
                    <div className="space-y-1.5">
                        <label htmlFor="nas_output_base" className="text-sm font-medium text-slate-700 dark:text-slate-300">NAS 預設輸出主目錄</label>
                        <input
                            id="nas_output_base"
                            type="text"
                            name="nas_output_base"
                            value={config.nas_output_base}
                            onChange={handleChange}
                            className="w-full bg-slate-50 dark:bg-[#1E293B] border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-2.5 focus:ring-2 focus:ring-[#3B82F6] focus:outline-none"
                        />
                    </div>
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
                        <label htmlFor="api_base_url" className="text-sm font-medium text-slate-700 dark:text-slate-300">API 伺服器網址 (Base URL)</label>
                        <input
                            id="api_base_url"
                            type="text"
                            name="api_base_url"
                            value={config.api_base_url}
                            onChange={handleChange}
                            className="w-full bg-slate-50 dark:bg-[#1E293B] border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-2.5 focus:ring-2 focus:ring-[#3B82F6] focus:outline-none"
                            placeholder="http://192.168.100.201:8045/v1/chat/completions"
                        />
                    </div>
                    <div className="space-y-1.5">
                        <label htmlFor="api_key" className="text-sm font-medium text-slate-700 dark:text-slate-300">API 金鑰 (API Key)</label>
                        <input
                            id="api_key"
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
                        <label htmlFor="proofread_model" className="text-sm font-medium text-slate-700 dark:text-slate-300">Gemini 模型選擇</label>
                        <select id="proofread_model" name="proofread_model" value={config.proofread_model} onChange={handleChange} className="w-full bg-slate-50 dark:bg-[#1E293B] border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-2.5 focus:ring-2 focus:ring-[#3B82F6] focus:outline-none">
                            <option value="gemini-3-flash">Gemini 3 Flash (快速)</option>
                            <option value="gemini-3-pro">Gemini 3 Pro (高階推理)</option>
                            <option value="gemini-3-pro-low">Gemini 3 Pro Low (低配版)</option>
                        </select>
                    </div>
                    <div className="space-y-1.5">
                        <label htmlFor="proofread_chunk_size" className="text-sm font-medium text-slate-700 dark:text-slate-300 flex justify-between">
                            <span>校對批次量</span>
                            <span className="text-xs text-slate-400">行/次</span>
                        </label>
                        <input
                            id="proofread_chunk_size"
                            type="number"
                            name="proofread_chunk_size"
                            value={config.proofread_chunk_size}
                            onChange={handleChange}
                            className="w-full bg-slate-50 dark:bg-[#1E293B] border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-2.5 focus:ring-2 focus:ring-[#3B82F6] focus:outline-none"
                        />
                    </div>
                    <div className="space-y-1.5">
                        <label htmlFor="punct_chunk_size" className="text-sm font-medium text-slate-700 dark:text-slate-300 flex justify-between">
                            <span>排版批次量</span>
                            <span className="text-xs text-slate-400">句/次</span>
                        </label>
                        <input
                            id="punct_chunk_size"
                            type="number"
                            name="punct_chunk_size"
                            value={config.punct_chunk_size}
                            onChange={handleChange}
                            className="w-full bg-slate-50 dark:bg-[#1E293B] border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-2.5 focus:ring-2 focus:ring-[#3B82F6] focus:outline-none"
                        />
                    </div>
                </div>

                <div className="space-y-1.5">
                    <label htmlFor="lecture_pdf" className="text-sm font-medium text-slate-700 dark:text-slate-300">上課講義 PDF 路徑 (NAS 絕對路徑)</label>
                    <div className="relative">
                        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                            <FileText size={16} className="text-slate-400" />
                        </div>
                        <input
                            id="lecture_pdf"
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
                    <label htmlFor="email_to" className="text-sm font-medium text-slate-700 dark:text-slate-300">收件人 Email (可用逗號分隔多人)</label>
                    <input
                        id="email_to"
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
