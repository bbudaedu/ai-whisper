# Phase 05 Plan 05: External Web UI History Interface Summary

## Summary
實作了外部 Web UI 的歷史任務查詢與下載介面。整合後端 `/api/tasks/history` 端點，讓使用者能透過視覺化介面回溯、追蹤並下載過去完成的語音轉錄成果。

- 建立 `TaskHistory.tsx` 頁面組件，支援任務列表顯示、詳情展開與多格式下載。
- 配置 `App.tsx` 路由，新增 `/history` 路徑。
- 更新 `Navigation.tsx` 導覽列，新增「歷史記錄」選單（含 Mobile 底部導覽）。
- 在 `Dashboard.tsx` 增加通往歷史紀錄的快捷按鈕。

## Key Decisions
- **採用分頁/輪詢機制**：`TaskHistory` 延續 `TaskTracker` 的設計，使用 `usePolling` 保持資料即時性，但將間隔拉長至 30 秒以平衡負擔。
- **統一視覺語言**：UI 組件與 `TaskTracker` 保持一致，確保操作體驗連貫。

## Key Files
- `web-ui-external/src/pages/TaskHistory.tsx` (New)
- `web-ui-external/src/App.tsx` (Modified)
- `web-ui-external/src/components/Navigation.tsx` (Modified)
- `web-ui-external/src/pages/Dashboard.tsx` (Modified)

## Metrics
- **Duration**: 20m
- **Tasks**: 2
- **Files**: 4

## Self-Check: PASSED
- [x] TaskHistory.tsx 組件已建立且包含下載連結。
- [x] 路由 `/history` 已註冊。
- [x] 導覽列已出現「歷史記錄」選單。
- [x] Dashboard 已有跳轉按鈕。

🤖 Generated with [Claude Code](https://claude.com/claude-code)
