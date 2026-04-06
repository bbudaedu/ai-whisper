import { useState, useEffect, useRef } from 'react';

const API_BASE = `http://${window.location.hostname}:8002/api`;

export default function LogViewer() {
    const [logType, setLogType] = useState('proofread');
    const [logs, setLogs] = useState<string[]>([]);
    const scrollRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const evtSource = new EventSource(`${API_BASE}/stream/${logType}`);

        evtSource.onmessage = function (event) {
            setLogs((prev) => [...prev, event.data]);
        };

        return () => {
            evtSource.close();
        };
    }, [logType]);

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [logs]);

    return (
        <div className="h-full flex flex-col bg-[#0d1117] rounded-2xl border border-slate-800 shadow-xl overflow-hidden font-mono text-sm">
            <div className="bg-[#161b22] px-4 py-3 flex items-center justify-between border-b border-slate-800 shrink-0">
                <div className="flex space-x-2">
                    <div className="w-3 h-3 rounded-full bg-red-500"></div>
                    <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
                    <div className="w-3 h-3 rounded-full bg-green-500"></div>
                </div>
                <div className="flex items-center space-x-2">
                    <label htmlFor="log_type_selector" className="sr-only">選擇日誌類型</label>
                    <select
                        id="log_type_selector"
                        value={logType}
                        onChange={(e) => {
                            setLogType(e.target.value);
                            setLogs([]);
                        }}
                        className="bg-[#21262d] text-slate-300 border border-slate-700 rounded-md px-3 py-1 text-xs focus:ring-1 focus:ring-indigo-500 focus:outline-none"
                    >
                        <option value="proofread">youtube_whisper.log (校對)</option>
                        <option value="whisper">youtube_whisper.log (轉錄)</option>
                        <option value="cron">youtube_whisper.log (排程)</option>
                    </select>
                </div>
            </div>
            <div ref={scrollRef} className="p-4 overflow-y-auto flex-1 text-slate-300 space-y-1">
                {logs.length === 0 ? (
                    <div className="text-slate-500 italic">等待日誌資料中...</div>
                ) : (
                    logs.map((line, i) => (
                        <div key={i} className={`whitespace-pre-wrap ${line.includes('ERROR') || line.includes('失敗') ? 'text-red-400' : line.includes('WARNING') ? 'text-yellow-400' : line.includes('完成') || line.includes('成功') ? 'text-green-400' : ''}`}>
                            {line}
                        </div>
                    ))
                )}
            </div>
        </div>
    );
}
