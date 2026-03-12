export interface EpisodeStatus {
    video_id: string;
    title: string;
    download_done: boolean;
    whisper_done: boolean;
    proofread_done: boolean;
    report_done: boolean;
    processed_at?: string;
}

export interface PlaylistStats {
    whispered: number;
    proofread: number;
    pending: number;
    total_videos?: number;
    processed_videos?: number; // Alias used in some UI components
    proofread_videos?: number; // Alias used in some UI components
}

export interface UrlDetectResult {
    type: 'video' | 'playlist';
    count: number;
    title?: string;
}

export interface VideoInfo {
    video_id: string;
    title: string;
    processed_at: string;
    proofread: boolean;
    playlist_id?: string;
}

export interface PlaylistData {
    id: string;
    name: string;
    url: string;
    output_dir: string;
    whisper_model: string;
    enabled: boolean;
    folder_prefix?: string;
    schedule: string;
    status: 'idle' | 'running' | 'paused' | 'error';
    last_run?: string; // Some legacy code might use this
    last_processed_at?: string;
    whisper_lang?: string;
    whisper_prompt?: string;
    proofread_prompt?: string;
    lecture_pdf?: string;
    batch_size?: number;
    track?: boolean;
    total_videos: number;
    stats: PlaylistStats;
    videos: VideoInfo[];
}

export interface GlobalStats {
    total_playlists: number;
    active_playlists: number;
    total_videos: number;
    total_proofread: number;
}

export interface DashboardData {
    playlists: PlaylistData[];
    global_stats: GlobalStats;
}

export interface EpisodeRecord {
    title?: string;
    downloaded?: boolean;
    transcribed?: boolean;
    proofread?: boolean;
    processed_at?: string;
    [key: string]: unknown;
}
