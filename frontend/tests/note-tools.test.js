const test = require('node:test');
const assert = require('node:assert/strict');
const {scaleNotes,closeGaps,audibleRanges,nextAudibleBeat} = require('../note-tools.js');
const n=(id,start,duration,track=0)=>({id,start,duration,track,pitch:60,articulation:'Legato'});
test('relative scaling preserves anchor, adjacency, attributes and unselected notes',()=>{
  const notes=[n('a',4,1),n('b',5,2),n('c',10,1,1)];
  const result=scaleNotes(notes,new Set(['a','b']),2);
  assert.deepEqual(result.map(x=>[x.start,x.duration]),[[4,2],[6,4],[10,1]]);
  assert.equal(result[2],notes[2]);assert.equal(notes[0].duration,1);assert.equal(result[0].articulation,'Legato');
});
test('absolute scaling and shrinking remain positive',()=>{
  const result=scaleNotes([n('a',4,1)],new Set(['a']),.5,false);
  assert.equal(result[0].start,2);assert.equal(result[0].duration,.5);
  assert.throws(()=>scaleNotes([],new Set(),NaN));assert.throws(()=>scaleNotes([],new Set(),0));
});
test('close only short positive gaps on same track, preserve chords and overlaps',()=>{
  const notes=[n('a',0,.95),n('b',0,2),n('c',1,1),n('d',.96,.02,1)];
  const result=closeGaps(notes,new Set(notes.map(n=>n.id)),.1);
  assert.equal(result[0].duration,1);assert.equal(result[1].duration,2);assert.equal(result[3],notes[3]);
});
test('selection does not bridge across an unselected intermediate note',()=>{
  const notes=[n('a',0,.8),n('b',1,.8),n('c',2,1)];
  assert.deepEqual(closeGaps(notes,new Set(['a','c']),2),notes);
});
test('gap threshold is strict and empty selection is a no-op',()=>{
  const notes=[n('a',0,.5),n('b',1,1)];
  assert.deepEqual(closeGaps(notes,new Set(['a','b']),.5),notes);
  assert.deepEqual(closeGaps(notes,new Set(),1),notes);
  assert.throws(()=>closeGaps(notes,new Set(),-1));
});
test('merged audible ranges preserve sustained overlapping notes',()=>{
  const ranges=audibleRanges([n('a',2,10),n('b',3,1),n('c',20,1)]);
  assert.deepEqual(ranges,[[1,13],[19,22]]);
  assert.equal(nextAudibleBeat(0,ranges),1);assert.equal(nextAudibleBeat(6,ranges),6);
  assert.equal(nextAudibleBeat(14,ranges),19);assert.equal(nextAudibleBeat(22,ranges),null);
});
test('invalid timing and empty playback do not create ranges',()=>{
  assert.deepEqual(audibleRanges([n('a',NaN,1),n('b',1,-1)]),[]);
  assert.equal(nextAudibleBeat(0,[]),null);
});
