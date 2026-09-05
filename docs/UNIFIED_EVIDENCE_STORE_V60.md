# SONICRAFT v6.0 Unified Evidence Store

## Purpose

v5.5-v5.9 introduced five useful but separate persistent evidence files.

The problem was no longer algorithm quality; it was long-term state governance.

v6.0 provides one transaction layer without changing the meaning of any evidence.

## Namespace contract

### utility_v55
Exact Context actual-render aggregate Utility.

### audit_v56
Counterfactual prune reliability.

### similarity_v57
Target <- donor analogy trust.

### archetype_v58
Aggregate cross-song performance-control evidence.

### mixture_v59
Soft-mixture component -> Context trust.

## Transaction format

The store uses:

- store schema 1
- canonical JSON payloads
- SHA-256 namespace identity
- zlib-compressed base64 blobs
- content deduplication
- commit DAG parent pointer
- 24-character commit ID derived from transaction body

The store contains no persistent legacy file paths.

## Crash recovery

Legacy evidence files are treated as a compatibility working set.

The Store HEAD is the last complete five-namespace transaction.

If startup detects any mismatch:
- drifted/invalid bytes are quarantined;
- every namespace is restored from HEAD;
- no partially updated state is accepted.

## Structural contamination validation

Evidence namespaces reject structural fields capable of carrying work content or identity.

The validator is recursive.

This is a governance guard, not an encryption feature.

## Export/import

Exports contain the complete path-independent Store.

Import validates:
- store version
- head existence
- referenced blob existence
- SHA-256
- decompression
- JSON parsing
- namespace schema
- contamination guard

Only after all validation passes is the current Store replaced.

## Compact

Compaction:
- retains a bounded recent commit history;
- keeps blobs referenced by retained commits;
- removes unreferenced blobs;
- naturally deduplicates identical namespace snapshots.

Default Auto-Loop retention is 32 commits.

## v4.9 Repair Policy

Repair Policy is intentionally outside this Store.

Reason:
Evidence answers, “what have we observed?”
Repair Policy answers, “how should the next candidate be generated?”

Mixing these layers would make provenance and rollback less clear.

A future policy checkpoint system may reference an Evidence Store commit, but should remain a separate namespace/type.
