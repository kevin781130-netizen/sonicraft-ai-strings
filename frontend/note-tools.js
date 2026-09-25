/* SONICRAFT note tools: independent implementation for the browser note model. */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.SonicraftNoteTools = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  function valid(note) {
    return Number.isFinite(note.start) && note.start >= 0 &&
      Number.isFinite(note.duration) && note.duration > 0;
  }
  function scaleNotes(notes, ids, factor, relative = true) {
    if (!Number.isFinite(factor) || factor <= 0) throw new Error('Scale must be positive.');
    const chosen = notes.filter(n => ids.has(n.id) && valid(n));
    if (!chosen.length) return notes;
    const anchor = relative ? Math.min(...chosen.map(n => n.start)) : 0;
    return notes.map(n => ids.has(n.id) && valid(n)
      ? {...n, start: anchor + (n.start - anchor) * factor, duration: n.duration * factor} : n);
  }
  // Extend only into a positive gap before the next onset on the SAME track.
  // Preserve chords, overlaps, unselected notes and existing note attributes.
  function closeGaps(notes, ids, threshold) {
    if (!Number.isFinite(threshold) || threshold <= 0) throw new Error('Threshold must be positive.');
    const tracks = new Map(), updates = new Map();
    for (const n of notes.filter(valid)) {
      if (!tracks.has(n.track)) tracks.set(n.track, []);
      tracks.get(n.track).push(n);
    }
    for (const sequence of tracks.values()) {
      sequence.sort((a, b) => a.start - b.start);
      const groups = [];
      for (const n of sequence) {
        if (!groups.length || groups.at(-1)[0].start !== n.start) groups.push([]);
        groups.at(-1).push(n);
      }
      for (let i = 0; i + 1 < groups.length; i++) {
        const next = groups[i + 1][0].start;
        if (!groups[i + 1].some(n => ids.has(n.id))) continue;
        for (const n of groups[i]) {
          const gap = next - (n.start + n.duration);
          if (ids.has(n.id) && gap > 1e-9 && gap < threshold)
            updates.set(n.id, {...n, duration: next - n.start});
        }
      }
    }
    return notes.map(n => updates.get(n.id) || n);
  }
  function audibleRanges(notes, padding = 1) {
    const ranges = notes.filter(valid).map(n => [Math.max(0, n.start - padding), n.start + n.duration + padding]);
    ranges.sort((a, b) => a[0] - b[0]);
    const merged = [];
    for (const r of ranges) {
      const previous = merged.at(-1);
      if (previous && r[0] <= previous[1]) previous[1] = Math.max(previous[1], r[1]);
      else merged.push([...r]);
    }
    return merged;
  }
  function nextAudibleBeat(beat, ranges) {
    for (const [start, end] of ranges) if (beat < end) return Math.max(beat, start);
    return null;
  }
  return {scaleNotes, closeGaps, audibleRanges, nextAudibleBeat};
});
