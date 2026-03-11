# Debugging Redo Failure and Path Issues

The user reported three issues:
1. Redoing episode 1 failed.
2. UI progress checkboxes are missing.
3. Background scheduler is processing episode 10.

## Hypotheses
- **Hypothesis 1 (Path Mismatch)**: The user changed `folder_prefix` from `T097S` to `T097V`. The existing folders on NAS are `T097S`. The script `get_episode_dir` uses the prefix. Since it can't find `T097V001`, it thinks it's not processed.
- **Hypothesis 2 (Empty Output Dir)**: The user set `output_dir` to `""`. If the script doesn't handle this, it might crash or use an unexpected path.
- **Hypothesis 3 (UI State)**: The UI checkboxes might be based on `processed_videos.json` or physical file existence. If the paths in `processed_videos.json` don't match the new config, the UI won't show them as completed.

## Proposed Investigation Steps
- [ ] Read `backend.log` and `auto_youtube_whisper.log`.
- [ ] Check `processed_videos.json` for path consistency after the user's manual edit.
- [ ] Check NAS directory structure (`/mnt/nas/Whisper_auto_rum/T097S`).
- [ ] Trace `auto_youtube_whisper.py` redo logic and path generation.

## Proposed Fixes
- Correct `config.json` (set `output_dir` back to a valid path or ensure `folder_prefix` matches directory names).
- Update `processed_videos.json` if necessary.
