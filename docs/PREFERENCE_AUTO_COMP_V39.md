# SONICRAFT v3.9 Preference-Guided Auto Comp

v3.9 turns Personal Taste into a conservative Locator comp assistant. It scans only unresolved phrases and submits one asynchronous A/B/C/D Audio Judge at a time, keeping GPU pressure bounded.

A phrase becomes an auto-commit candidate only when all gates pass: Personal Taste enabled, current profile identity matches the Judge result, profile confidence >= Min Confidence, winner-vs-runner-up personalized score margin >= Min Margin, and winner Safety >= Safety Floor. Anything else is counted as Needs Review.

Candidates are not written immediately. When the whole Locator queue completes, all accepted phrase/take pairs are written through one fixed-memory `commitBatch`, producing one internal Undo snapshot. Cancel stops future judging and discards uncommitted candidates. Auto-committed decisions are deliberately **not** fed into Judge Memory, preventing self-training loops; only explicit human Favorite/Reject/Commit actions teach Personal Taste.
