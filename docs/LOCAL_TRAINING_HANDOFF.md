# 本機訓練與實機驗收交接

## 狀態界線

2026-09-21 檢查時，`main` 仍在 `5c2f168`；整合版位於 PR #6，
commit `68068a54af3a9a6c5f5029a67a3c5c0a8d339fe2`。
該整合版的四個 GitHub Actions 檢查均成功，包含 Windows VST3 編譯與官方
Validator。這是特定 CI 產物的驗證，不是本機 DAW、GPU 或聲學品質驗收。

本次追加修正：

- 訓練、控制面板與暫停／恢復入口統一優先使用專案 `.venv`。
- Windows 啟動器保留訓練程式的退出碼，避免括號區塊提前展開 `%errorlevel%`。
- 環境建立／套件安裝失敗時立即停止，不再印出準備完成。
- 預檢覆蓋驗證集路徑、自訂暫停狀態、輸出目錄誤用與最佳／最後 checkpoint 路徑衝突。
- 最終放行拒絕空物件、錯誤 JSON 型別及字串形式的模型批准值；異常資料會撤銷舊批准標記。
- 盲聽證據必須同時通過 sample size、realism、technique identity、negative control。
- CI 加入最終放行破壞測試，以及使用實際 Windows cmd.exe 的啟動器行為測試。

## 正確執行順序

1. 使用包含本次修正及 PR #6 的整合版本。不要只下載尚未合併更新的舊 `main`。
2. 執行 `scripts\SETUP_TRAINING.bat`。此步安裝訓練環境，CUDA 與顯卡相容性
   仍由下一步在本機驗證。資料集、音檔及正式權重不在 Git 內。
3. 依 `SCHEMA8_PRODUCTION_RUNBOOK.md` 複製並填寫 release plan，執行：

   ```bat
   .venv\Scripts\python.exe training\scripts\schema8_release_status.py --plan schema8_release_plan.local.json
   ```

   若顯示 `WAITING_FOR_STATIC_INPUTS`，先準備合法訓練資料、latent index、
   curriculum／provenance 與 baseline checkpoints。不能直接宣稱只欠 GPU 運算。
4. 以 `TRAIN_RENDERER_GPU.bat` 加上真實 index、validation index、preset 及輸出路徑
   啟動 HQ 訓練；Compact/Frontier 蒸餾及 phrase fine-tuning 請遵循 Schema 8 文件。
   最終 checkpoint 路徑必須和 release plan 一致。
5. 需要暫停時執行 `PAUSE_TRAINING.bat`，等狀態成為 `paused` 才釋放 GPU／關機；
   執行 `RESUME_TRAINING.bat` 復原。中途暫停的 epoch 會重新抽樣重跑。
6. 依 production runbook 執行 transition evaluate／promote，以正式 candidate
   渲染盲聽音檔並收集真實受試者結果，再 preflight／seal／manifest／gate。
7. 執行 Windows RC／ProductShell、Cubase、Studio One、RTX 5090 和獨立盲聽 QA。
   用 `RC_EVIDENCE_STATUS_V70.bat` 查看缺件，最後執行 `FINAL_GATE_V70.bat`。
8. 公開發行另需簽章；簽章改變 binary hash，必須重產對應的驗收證據，再執行
   `VERIFY_AUTHENTICODE_V70.bat` 與 `PUBLIC_RELEASE_GATE_V70.bat`。

## 能與不能宣稱的完成範圍

軟體／CI 通過表示已可交接本機準備與驗證；不保證未提供的資料、驅動程式、
顯存、最終權重或音質會通過。除了訓練，仍有真人盲聽、DAW／ProductShell 實機
驗證和公開發行簽章。自然／人工泛音細分及 con sordino 的既有語意缺口仍屬
post-v7 範圍，不能當成已訓練完成的能力。

所有 smoke 使用的假資料都只存在暫存目錄，不能作為正式放行證據。
