from __future__ import annotations
import socket, struct
from dataclasses import dataclass
from typing import BinaryIO

MAGIC_REQ = b'SAIR'
MAGIC_RESP = b'SAOR'
VERSION = 1
TYPE_RENDER = 1
TYPE_PING = 2
TYPE_JUDGE = 3
TYPE_PREFERENCE = 4
TYPE_PROFILE_QUERY = 5
TYPE_PROFILE_CLEAR = 6
STATUS_OK = 0
STATUS_MODEL_NOT_READY = 1
STATUS_BAD_REQUEST = 2
STATUS_INTERNAL_ERROR = 3
STATUS_CACHE_HIT = 4

# <4sHHQqqIIHHffI = 56 bytes
REQ_HEADER = struct.Struct('<4sHHQqqIIHHffI')
# event: project_sample, type, part, note, articulation, velocity, tempo, 14 controls
EVENT = struct.Struct('<qBBBBff14f')
# v3.7 Take Judge request payload, sent immediately after the standard request header:
# base_nonce float32, favorite_mask u8, reject_mask u8, reserved u16.
JUDGE_CONFIG = struct.Struct('<fBBH')
# v3.7 fixed response: version u16, winner u8, valid_mask u8,
# then A/B/C/D x [overall,dynamics,attack,transition,stability,safety].
JUDGE_RESULT = struct.Struct('<HBB24f')
JUDGE_RESULT_VERSION = 1
# v3.8 capability in JUDGE_CONFIG.reserved. Legacy clients send zero.
JUDGE_CAP_PERSONAL = 0x8000
JUDGE_PERSONAL_ENABLED = 0x4000
JUDGE_STRENGTH_MASK = 0x00FF
# v2 result adds A-D personalized score, profile confidence/evidence and 5 explainable weights.
JUDGE_RESULT_V2 = struct.Struct('<HBB34fI')  # exactly 144 bytes; low32 profile hash guards stale multi-instance results
JUDGE_RESULT_V2_VERSION = 2
# preference event: kind u8 (1 fav,2 reject,3 commit), take u8, reserved u16, then 24 judge metric floats.
PREFERENCE_EVENT = struct.Struct('<BBH24f')
PROFILE_RESULT = struct.Struct('<HHQff5f')  # version, reserved, profile_hash, confidence, evidence, weights
PROFILE_RESULT_VERSION = 1

# <4sHHQqIIHHQ = 44 bytes
RESP_HEADER = struct.Struct('<4sHHQqIIHHQ')

EVENT_NOTE_ON = 1
EVENT_NOTE_OFF = 2
EVENT_KEYSWITCH = 3
EVENT_CONTROL = 4
EVENT_RESET = 5

@dataclass(slots=True)
class RequestHeader:
    msg_type: int
    request_id: int
    start_sample: int
    end_sample: int
    sample_rate: int
    event_count: int
    part_count: int
    mode: int
    tempo_bpm: float
    lookahead: float
    flags: int = 0

@dataclass(slots=True)
class ResponseHeader:
    status: int
    request_id: int
    start_sample: int
    frames: int
    sample_rate: int
    channels: int
    flags: int
    payload_bytes: int

def recv_exact(sock: socket.socket, n: int) -> bytes:
    out = bytearray(n)
    view = memoryview(out)
    pos = 0
    while pos < n:
        got = sock.recv_into(view[pos:], n-pos)
        if got <= 0:
            raise ConnectionError('peer closed')
        pos += got
    return bytes(out)

def pack_request_header(h: RequestHeader) -> bytes:
    return REQ_HEADER.pack(MAGIC_REQ, VERSION, h.msg_type, h.request_id,
                           h.start_sample, h.end_sample, h.sample_rate, h.event_count,
                           h.part_count, h.mode, h.tempo_bpm, h.lookahead, h.flags)

def unpack_request_header(data: bytes) -> RequestHeader:
    magic, version, msg_type, req, start, end, sr, ne, pc, mode, tempo, look, flags = REQ_HEADER.unpack(data)
    if magic != MAGIC_REQ or version != VERSION:
        raise ValueError('bad protocol header')
    return RequestHeader(msg_type, req, start, end, sr, ne, pc, mode, tempo, look, flags)

def pack_response_header(h: ResponseHeader) -> bytes:
    return RESP_HEADER.pack(MAGIC_RESP, VERSION, h.status, h.request_id,
                            h.start_sample, h.frames, h.sample_rate, h.channels,
                            h.flags, h.payload_bytes)

def unpack_response_header(data: bytes) -> ResponseHeader:
    magic, version, status, req, start, frames, sr, ch, flags, n = RESP_HEADER.unpack(data)
    if magic != MAGIC_RESP or version != VERSION:
        raise ValueError('bad response header')
    return ResponseHeader(status, req, start, frames, sr, ch, flags, n)
