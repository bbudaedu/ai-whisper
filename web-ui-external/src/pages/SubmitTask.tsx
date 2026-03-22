import { useState } from 'react';
import { Upload, Link as LinkIcon, FileAudio, Youtube, Settings2, FileText, CheckCircle2 } from 'lucide-react';
import api from '../api/client';

export default function SubmitTask() {
  const [mode, setMode] = useState<'upload' | 'youtube'>('upload');
  const [file, setFile] = useState<File | null>(null);
  const [url, setUrl] = useState('');
  const [audioNature, setAudioNature] = useState('會議');
  const [prompt, setPrompt] = useState('請將這段語音轉為文字。');
  const [formats, setFormats] = useState({
    txt: true,
    srt: true,
    word: true,
    excel: true,
    json: true,
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');
  const [errorMessage, setErrorMessage] = useState('');

  const isPlaylist = url.includes('list=');

  const handleFormatChange = (format: keyof typeof formats) => {
    setFormats((prev) => ({ ...prev, [format]: !prev[format] }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setSuccessMessage('');
    setErrorMessage('');

    const selectedFormats = Object.entries(formats)
      .filter(([_, isSelected]) => isSelected)
      .map(([format]) => format);

    try {
      const payloadData = {
        prompt,
        audio_nature: audioNature,
        url: mode === 'youtube' ? url : undefined,
      };

      if (mode === 'upload') {
        if (!file) {
          throw new Error('請選擇一個檔案');
        }
        const formData = new FormData();
        formData.append('type', 'upload');
        formData.append('source', 'external');
        formData.append('payload', JSON.stringify(payloadData));
        formData.append('output_formats', JSON.stringify(selectedFormats));
        formData.append('file', file);

        await api.post('/tasks/', formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        });
      } else {
        if (!url) {
          throw new Error('請輸入 YouTube 網址');
        }
        await api.post('/tasks/', {
          type: 'youtube',
          source: 'external',
          payload: payloadData,
          output_formats: selectedFormats,
        });
      }

      setSuccessMessage('任務提交成功！');
      setFile(null);
      setUrl('');
    } catch (err: any) {
      setErrorMessage(err.response?.data?.detail || err.message || '任務提交失敗');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6 pb-20">
      <div className="bg-white dark:bg-[#161b22] rounded-2xl border border-gray-200 dark:border-gray-800 shadow-sm overflow-hidden">
        <div className="p-6 border-b border-gray-200 dark:border-gray-800">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white flex items-center gap-2">
            <Settings2 className="w-5 h-5 text-blue-500" />
            提交新任務
          </h2>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            上傳音檔或提供 YouTube 網址以進行語音轉文字與校對處理
          </p>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-8">
          {successMessage && (
            <div className="p-4 rounded-xl bg-green-50 dark:bg-green-500/10 border border-green-200 dark:border-green-500/20 text-green-700 dark:text-green-400 flex items-center gap-3">
              <CheckCircle2 className="w-5 h-5" />
              {successMessage}
            </div>
          )}

          {errorMessage && (
            <div className="p-4 rounded-xl bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/20 text-red-700 dark:text-red-400">
              {errorMessage}
            </div>
          )}

          {/* Mode Toggle */}
          <div className="flex p-1 space-x-1 bg-gray-100 dark:bg-gray-800/50 rounded-xl">
            <button
              type="button"
              onClick={() => setMode('upload')}
              className={`flex-1 flex items-center justify-center gap-2 py-2.5 text-sm font-medium rounded-lg transition-colors ${
                mode === 'upload'
                  ? 'bg-white dark:bg-gray-800 text-gray-900 dark:text-white shadow-sm'
                  : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300'
              }`}
            >
              <Upload className="w-4 h-4" />
              上傳檔案
            </button>
            <button
              type="button"
              onClick={() => setMode('youtube')}
              className={`flex-1 flex items-center justify-center gap-2 py-2.5 text-sm font-medium rounded-lg transition-colors ${
                mode === 'youtube'
                  ? 'bg-white dark:bg-gray-800 text-gray-900 dark:text-white shadow-sm'
                  : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300'
              }`}
            >
              <Youtube className="w-4 h-4" />
              YouTube 網址
            </button>
          </div>

          {/* Input Source */}
          <div className="space-y-4">
            <h3 className="text-sm font-medium text-gray-900 dark:text-white flex items-center gap-2">
              {mode === 'upload' ? (
                <><FileAudio className="w-4 h-4 text-blue-500" /> 音檔來源</>
              ) : (
                <><LinkIcon className="w-4 h-4 text-blue-500" /> 影片來源</>
              )}
            </h3>

            {mode === 'upload' ? (
              <div className="flex items-center justify-center w-full">
                <label className="flex flex-col items-center justify-center w-full h-40 border-2 border-dashed rounded-xl cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800/50 border-gray-300 dark:border-gray-700 transition-colors">
                  <div className="flex flex-col items-center justify-center pt-5 pb-6">
                    <Upload className="w-8 h-8 mb-3 text-gray-400" />
                    <p className="mb-2 text-sm text-gray-500 dark:text-gray-400">
                      <span className="font-semibold">點擊上傳</span> 或拖曳檔案至此
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      支援 MP3, M4A, WAV 等格式
                    </p>
                    {file && (
                      <p className="mt-2 text-sm font-medium text-blue-600 dark:text-blue-400">
                        已選擇: {file.name}
                      </p>
                    )}
                  </div>
                  <input
                    type="file"
                    className="hidden"
                    accept="audio/*,video/*"
                    onChange={(e) => setFile(e.target.files?.[0] || null)}
                  />
                </label>
              </div>
            ) : (
              <div className="space-y-2">
                <input
                  type="url"
                  placeholder="https://www.youtube.com/watch?v=... 或 https://youtube.com/playlist?list=..."
                  className="w-full px-4 py-2.5 bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all dark:text-white"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                />
                {url && isPlaylist && (
                  <div className="text-sm text-blue-600 dark:text-blue-400 flex items-center gap-1.5 bg-blue-50 dark:bg-blue-500/10 p-2 rounded-lg inline-flex">
                    <Youtube className="w-4 h-4" />
                    自動偵測為播放清單 (Playlist)
                  </div>
                )}
                {url && !isPlaylist && (
                  <div className="text-sm text-gray-500 dark:text-gray-400 flex items-center gap-1.5 bg-gray-50 dark:bg-gray-800 p-2 rounded-lg inline-flex">
                    <Youtube className="w-4 h-4" />
                    自動偵測為單一影片 (Single Video)
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Parameters */}
          <div className="space-y-4">
            <h3 className="text-sm font-medium text-gray-900 dark:text-white flex items-center gap-2">
              <Settings2 className="w-4 h-4 text-blue-500" /> 參數設定
            </h3>

            <div className="space-y-4">
              <div>
                <label className="block text-sm text-gray-700 dark:text-gray-300 mb-1.5">
                  音檔性質
                </label>
                <select
                  className="w-full md:w-1/2 px-4 py-2.5 bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all dark:text-white"
                  value={audioNature}
                  onChange={(e) => setAudioNature(e.target.value)}
                >
                  <option value="會議">會議</option>
                  <option value="佛學課程">佛學課程</option>
                </select>
              </div>

              <div>
                <label className="block text-sm text-gray-700 dark:text-gray-300 mb-1.5">
                  Prompt提示詞
                </label>
                <textarea
                  rows={3}
                  className="w-full px-4 py-3 bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all dark:text-white resize-none"
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  placeholder="輸入提供給 Whisper 的 Prompt 以提升辨識準確率..."
                />
              </div>
            </div>
          </div>

          {/* Output Formats */}
          <div className="space-y-4">
            <h3 className="text-sm font-medium text-gray-900 dark:text-white flex items-center gap-2">
              <FileText className="w-4 h-4 text-blue-500" /> 輸出格式
            </h3>
            <div className="flex flex-wrap gap-4">
              {(Object.keys(formats) as Array<keyof typeof formats>).map((format) => (
                <label key={format} className="flex items-center gap-2 cursor-pointer group">
                  <div className={`w-5 h-5 rounded border flex items-center justify-center transition-colors ${
                    formats[format]
                      ? 'bg-blue-500 border-blue-500 text-white'
                      : 'bg-white dark:bg-gray-900 border-gray-300 dark:border-gray-600'
                  }`}>
                    {formats[format] && <CheckCircle2 className="w-3.5 h-3.5" />}
                  </div>
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300 uppercase select-none group-hover:text-gray-900 dark:group-hover:text-white transition-colors">
                    {format}
                  </span>
                  <input
                    type="checkbox"
                    className="hidden"
                    checked={formats[format]}
                    onChange={() => handleFormatChange(format)}
                  />
                </label>
              ))}
            </div>
          </div>

          <div className="pt-4 border-t border-gray-200 dark:border-gray-800">
            <button
              type="submit"
              disabled={isSubmitting || (mode === 'upload' && !file) || (mode === 'youtube' && !url)}
              className="w-full py-3 px-4 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 dark:disabled:bg-blue-800 disabled:cursor-not-allowed text-white font-medium rounded-xl transition-colors focus:outline-none focus:ring-4 focus:ring-blue-500/20 shadow-sm flex items-center justify-center gap-2"
            >
              {isSubmitting ? (
                <>
                  <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  提交中...
                </>
              ) : (
                '提交任務'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
