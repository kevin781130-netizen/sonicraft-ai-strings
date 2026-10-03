#pragma once
#include <algorithm>
#include <array>
#include <cctype>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <limits>
#include <string>
#include <utility>
#include <vector>

namespace Sonicraft::ScoreV70 {

struct Note {
    int part = 0;          // 0 Vln I, 1 Vln II, 2 Viola, 3 Cello
    int pitch = 60;        // MIDI note
    std::uint32_t startTick = 0;
    std::uint32_t durationTick = 1;
    int velocity = 90;
    int articulation = 0;  // Sustain..Flautando
};

struct Document {
    int ppq = 480;
    std::vector<Note> notes;

    std::array<int,4> sectionCounts() const noexcept {
        std::array<int,4> out{{0,0,0,0}};
        for (const auto& n : notes) if (n.part >= 0 && n.part < 4) ++out[static_cast<std::size_t>(n.part)];
        return out;
    }

    bool edit(std::size_t index, int part, int pitch, std::uint32_t durationTick,
              int velocity, int articulation) noexcept {
        if (index >= notes.size() || part < 0 || part > 3 || pitch < 0 || pitch > 127 ||
            durationTick == 0 || velocity < 1 || velocity > 127 ||
            articulation < 0 || articulation > 11) return false;
        auto& n = notes[index];
        n.part = part;
        n.pitch = pitch;
        n.durationTick = durationTick;
        n.velocity = velocity;
        n.articulation = articulation;
        return true;
    }
};

inline int stringPartForMidiChannel(int ch) noexcept {
    if (ch >= 0 && ch < 4) return ch;
    if (ch >= 4 && ch <= 6) return 0;
    if (ch >= 7 && ch <= 9) return 1;
    if (ch >= 10 && ch <= 12) return 2;
    if (ch >= 13 && ch <= 15) return 3;
    return -1;
}

namespace detail {

inline std::uint16_t be16(const std::vector<std::uint8_t>& b, std::size_t p) {
    return static_cast<std::uint16_t>((std::uint16_t(b[p]) << 8) | b[p + 1]);
}
inline std::uint32_t be32(const std::vector<std::uint8_t>& b, std::size_t p) {
    return (std::uint32_t(b[p]) << 24) | (std::uint32_t(b[p + 1]) << 16) |
           (std::uint32_t(b[p + 2]) << 8) | std::uint32_t(b[p + 3]);
}
inline bool varLen(const std::vector<std::uint8_t>& b, std::size_t& p, std::size_t end, std::uint32_t& out) {
    out = 0;
    for (int i = 0; i < 4; ++i) {
        if (p >= end) return false;
        const auto v = b[p++];
        out = (out << 7) | (v & 0x7Fu);
        if ((v & 0x80u) == 0) return true;
    }
    return false;
}
inline std::uint32_t clampTick(std::uint64_t v) {
    return static_cast<std::uint32_t>(std::min<std::uint64_t>(v, std::numeric_limits<std::uint32_t>::max()));
}
inline bool readBytes(const std::filesystem::path& path, std::vector<std::uint8_t>& out) {
    std::ifstream f(path, std::ios::binary);
    if (!f) return false;
    f.seekg(0, std::ios::end);
    const auto n = f.tellg();
    if (n < 0) return false;
    f.seekg(0, std::ios::beg);
    out.resize(static_cast<std::size_t>(n));
    if (!out.empty()) f.read(reinterpret_cast<char*>(out.data()), static_cast<std::streamsize>(out.size()));
    return bool(f) || out.empty();
}
inline bool readText(const std::filesystem::path& path, std::string& out) {
    std::ifstream f(path, std::ios::binary);
    if (!f) return false;
    out.assign(std::istreambuf_iterator<char>(f), std::istreambuf_iterator<char>());
    return bool(f) || !out.empty();
}
inline std::string tagValue(const std::string& s, const char* tag, std::size_t from = 0) {
    const std::string open = std::string("<") + tag + ">";
    const std::string close = std::string("</") + tag + ">";
    const auto a = s.find(open, from);
    if (a == std::string::npos) return {};
    const auto b = s.find(close, a + open.size());
    if (b == std::string::npos) return {};
    return s.substr(a + open.size(), b - (a + open.size()));
}
inline int toInt(const std::string& s, int fallback) {
    try {
        std::size_t used = 0;
        const int v = std::stoi(s, &used);
        return used ? v : fallback;
    } catch (...) { return fallback; }
}
inline std::uint32_t scaledTicks(int duration, int divisions, int ppq) {
    if (duration <= 0 || divisions <= 0 || ppq <= 0) return 1;
    const std::uint64_t n = std::uint64_t(duration) * std::uint64_t(ppq);
    return static_cast<std::uint32_t>(std::max<std::uint64_t>(1, (n + std::uint64_t(divisions / 2)) / std::uint64_t(divisions)));
}
inline int pitchFromXml(const std::string& noteBlock) {
    const auto stepText = tagValue(noteBlock, "step");
    const int octave = toInt(tagValue(noteBlock, "octave"), 4);
    const int alter = toInt(tagValue(noteBlock, "alter"), 0);
    if (stepText.empty()) return -1;
    int semitone = 0;
    switch (static_cast<char>(std::toupper(static_cast<unsigned char>(stepText[0])))) {
        case 'C': semitone = 0; break; case 'D': semitone = 2; break;
        case 'E': semitone = 4; break; case 'F': semitone = 5; break;
        case 'G': semitone = 7; break; case 'A': semitone = 9; break;
        case 'B': semitone = 11; break; default: return -1;
    }
    return std::clamp((octave + 1) * 12 + semitone + alter, 0, 127);
}
inline int articulationFromXml(const std::string& n) {
    if (n.find("<flaut") != std::string::npos) return 11;
    if (n.find("<harmonic") != std::string::npos) return 10;
    if (n.find("<trill") != std::string::npos) return 9;
    if (n.find("pizz") != std::string::npos || n.find("<pluck") != std::string::npos) return 8;
    if (n.find("<tremolo") != std::string::npos) return 7;
    if (n.find("<spiccato") != std::string::npos) return 6;
    if (n.find("<staccato") != std::string::npos) return 5;
    if (n.find("<accent") != std::string::npos || n.find("<strong-accent") != std::string::npos) return 4;
    if (n.find("<glissando") != std::string::npos || n.find("<slide") != std::string::npos) return 2;
    if (n.find("<slur") != std::string::npos || n.find("<tenuto") != std::string::npos) return 1;
    return 0;
}

} // namespace detail

inline bool importMidi(const std::vector<std::uint8_t>& bytes, Document& out, std::string& error) {
    out = {};
    if (bytes.size() < 14 || std::string(reinterpret_cast<const char*>(bytes.data()), 4) != "MThd") {
        error = "Not a Standard MIDI File (missing MThd).";
        return false;
    }
    const auto headerLen = detail::be32(bytes, 4);
    if (headerLen < 6 || 8u + headerLen > bytes.size()) {
        error = "Invalid MIDI header length.";
        return false;
    }
    const auto trackCount = detail::be16(bytes, 10);
    const auto division = detail::be16(bytes, 12);
    if ((division & 0x8000u) != 0 || division == 0) {
        error = "SMPTE-time MIDI is not supported by the score editor.";
        return false;
    }
    out.ppq = division;

    std::size_t p = 8u + headerLen;
    for (std::uint16_t track = 0; track < trackCount; ++track) {
        if (p + 8 > bytes.size() || std::string(reinterpret_cast<const char*>(bytes.data() + p), 4) != "MTrk") {
            error = "Invalid MIDI track chunk.";
            return false;
        }
        const auto len = detail::be32(bytes, p + 4);
        p += 8;
        if (p + len > bytes.size()) {
            error = "Truncated MIDI track.";
            return false;
        }
        const std::size_t end = p + len;
        std::uint64_t tick = 0;
        std::uint8_t running = 0;
        std::array<int,4> currentArt{{0,0,0,0}};
        struct Active { std::uint32_t tick; int velocity; int articulation; };
        std::array<std::vector<Active>, 16 * 128> active{};

        while (p < end) {
            std::uint32_t delta = 0;
            if (!detail::varLen(bytes, p, end, delta)) { error = "Invalid MIDI delta-time."; return false; }
            tick += delta;
            if (p >= end) break;

            std::uint8_t status = bytes[p];
            if (status & 0x80u) {
                ++p;
                if (status < 0xF0u) running = status;
            } else {
                if (!running) { error = "MIDI running status without prior status."; return false; }
                status = running;
            }

            if (status == 0xFFu) {
                if (p >= end) { error = "Truncated MIDI meta event."; return false; }
                ++p; // meta type
                std::uint32_t n = 0;
                if (!detail::varLen(bytes, p, end, n) || p + n > end) { error = "Truncated MIDI meta payload."; return false; }
                p += n;
                continue;
            }
            if (status == 0xF0u || status == 0xF7u) {
                std::uint32_t n = 0;
                if (!detail::varLen(bytes, p, end, n) || p + n > end) { error = "Truncated MIDI SysEx."; return false; }
                p += n;
                running = 0;
                continue;
            }

            const int kind = status & 0xF0;
            const int ch = status & 0x0F;
            const int need = (kind == 0xC0 || kind == 0xD0) ? 1 : 2;
            if (p + static_cast<std::size_t>(need) > end) { error = "Truncated MIDI channel event."; return false; }
            const int d1 = bytes[p++];
            const int d2 = need == 2 ? bytes[p++] : 0;
            const int part = stringPartForMidiChannel(ch);

            if (part >= 0 && kind == 0x90 && d2 > 0) {
                if (d1 >= 24 && d1 < 36) {
                    currentArt[static_cast<std::size_t>(part)] = d1 - 24;
                } else {
                    active[static_cast<std::size_t>(ch * 128 + d1)].push_back(
                        {detail::clampTick(tick), d2, currentArt[static_cast<std::size_t>(part)]});
                }
            } else if (part >= 0 && (kind == 0x80 || (kind == 0x90 && d2 == 0))) {
                auto& stack = active[static_cast<std::size_t>(ch * 128 + d1)];
                if (!stack.empty()) {
                    const auto a = stack.back();
                    stack.pop_back();
                    const auto endTick = detail::clampTick(tick);
                    Note n{};
                    n.part = part; n.pitch = d1; n.startTick = a.tick;
                    n.durationTick = std::max<std::uint32_t>(1, endTick >= a.tick ? endTick - a.tick : 1);
                    n.velocity = a.velocity; n.articulation = a.articulation;
                    out.notes.push_back(n);
                }
            }
        }
        p = end;
    }

    std::sort(out.notes.begin(), out.notes.end(), [](const Note& a, const Note& b) {
        if (a.startTick != b.startTick) return a.startTick < b.startTick;
        if (a.part != b.part) return a.part < b.part;
        return a.pitch < b.pitch;
    });
    if (out.notes.empty()) {
        error = "MIDI imported successfully but contains no playable string notes.";
        return false;
    }
    error.clear();
    return true;
}

inline bool importMidiFile(const std::filesystem::path& path, Document& out, std::string& error) {
    std::vector<std::uint8_t> bytes;
    if (!detail::readBytes(path, bytes)) { error = "Could not read MIDI file."; return false; }
    return importMidi(bytes, out, error);
}

inline bool importMusicXml(const std::string& xml, Document& out, std::string& error) {
    out = {};
    out.ppq = 480;
    if (xml.find("<score-partwise") == std::string::npos && xml.find("<score-timewise") == std::string::npos) {
        error = "Not a MusicXML score.";
        return false;
    }

    std::size_t search = 0;
    int partIndex = 0;
    while (partIndex < 4) {
        const auto partStart = xml.find("<part", search);
        if (partStart == std::string::npos) break;
        const auto tagEnd = xml.find('>', partStart);
        if (tagEnd == std::string::npos) break;
        // Skip <part-list> and <part-name>; only accept a real <part ...> container.
        const auto afterName = partStart + 5;
        if (afterName < xml.size() && xml[afterName] != ' ' && xml[afterName] != '>') {
            search = tagEnd + 1;
            continue;
        }
        const auto partEnd = xml.find("</part>", tagEnd);
        if (partEnd == std::string::npos) { error = "Unterminated MusicXML part."; return false; }
        const std::string body = xml.substr(tagEnd + 1, partEnd - (tagEnd + 1));

        int divisions = 1;
        std::uint64_t cursor = 0;
        std::uint64_t lastStart = 0;
        std::size_t p = 0;
        while (p < body.size()) {
            const auto nNote = body.find("<note", p);
            const auto nBackup = body.find("<backup", p);
            const auto nForward = body.find("<forward", p);
            const auto nDiv = body.find("<divisions>", p);
            const auto next = std::min({nNote, nBackup, nForward, nDiv});
            if (next == std::string::npos) break;

            if (next == nDiv) {
                const auto close = body.find("</divisions>", next);
                if (close == std::string::npos) break;
                divisions = std::max(1, detail::toInt(body.substr(next + 11, close - (next + 11)), divisions));
                p = close + 12;
                continue;
            }

            if (next == nBackup || next == nForward) {
                const char* closeTag = next == nBackup ? "</backup>" : "</forward>";
                const auto close = body.find(closeTag, next);
                if (close == std::string::npos) break;
                const auto block = body.substr(next, close + std::char_traits<char>::length(closeTag) - next);
                const auto dt = detail::scaledTicks(detail::toInt(detail::tagValue(block, "duration"), 0), divisions, out.ppq);
                if (next == nBackup) cursor = cursor > dt ? cursor - dt : 0;
                else cursor += dt;
                p = close + std::char_traits<char>::length(closeTag);
                continue;
            }

            const auto noteEnd = body.find("</note>", nNote);
            if (noteEnd == std::string::npos) { error = "Unterminated MusicXML note."; return false; }
            const auto block = body.substr(nNote, noteEnd + 7 - nNote);
            const auto duration = detail::scaledTicks(detail::toInt(detail::tagValue(block, "duration"), 1), divisions, out.ppq);
            const bool chord = block.find("<chord") != std::string::npos;
            const std::uint64_t startTick = chord ? lastStart : cursor;
            if (!chord) { lastStart = cursor; cursor += duration; }

            if (block.find("<rest") == std::string::npos) {
                const int pitch = detail::pitchFromXml(block);
                if (pitch >= 0) {
                    Note n{};
                    n.part = partIndex; n.pitch = pitch;
                    n.startTick = detail::clampTick(startTick);
                    n.durationTick = duration;
                    n.velocity = std::clamp(detail::toInt(detail::tagValue(block, "velocity"), 90), 1, 127);
                    n.articulation = detail::articulationFromXml(block);
                    out.notes.push_back(n);
                }
            }
            p = noteEnd + 7;
        }

        ++partIndex;
        search = partEnd + 7;
    }

    std::sort(out.notes.begin(), out.notes.end(), [](const Note& a, const Note& b) {
        if (a.startTick != b.startTick) return a.startTick < b.startTick;
        if (a.part != b.part) return a.part < b.part;
        return a.pitch < b.pitch;
    });
    if (out.notes.empty()) {
        error = "MusicXML contains no playable notes in the first four parts.";
        return false;
    }
    error.clear();
    return true;
}

inline bool importMusicXmlFile(const std::filesystem::path& path, Document& out, std::string& error) {
    std::string xml;
    if (!detail::readText(path, xml)) { error = "Could not read MusicXML file."; return false; }
    return importMusicXml(xml, out, error);
}

} // namespace Sonicraft::ScoreV70
