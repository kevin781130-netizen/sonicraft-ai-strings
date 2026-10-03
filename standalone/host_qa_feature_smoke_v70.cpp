#include "../src/score_document_v70.h"
#include "../standalone/realtime_shell_core.h"
#include <array>
#include <cassert>
#include <cstdint>
#include <iostream>
#include <string>
#include <vector>

using namespace Sonicraft::ScoreV70;
using namespace Sonicraft::ProductShell;

static std::vector<std::uint8_t> midiFixture() {
    // Format 0, PPQ=480. Four channels each play one quarter note.
    const std::uint8_t raw[] = {
        'M','T','h','d', 0,0,0,6, 0,0, 0,1, 0x01,0xE0,
        'M','T','r','k', 0,0,0,36,
        0x00,0x90,60,100, 0x83,0x60,0x80,60,0,
        0x00,0x91,62,100, 0x83,0x60,0x81,62,0,
        0x00,0x92,64,100, 0x83,0x60,0x82,64,0,
        0x00,0x93,48,100, 0x83,0x60,0x83,48,0,
        0x00,0xFF,0x2F,0x00
    };
    return {std::begin(raw), std::end(raw)};
}

int main() {
    {
        Document d; std::string error;
        const auto midi = midiFixture();
        assert(importMidi(midi, d, error));
        assert(d.notes.size() == 4);
        const auto counts = d.sectionCounts();
        assert((counts == std::array<int,4>{{1,1,1,1}}));
        assert(d.edit(2, 2, 67, 240, 96, 5));
        assert(d.notes[2].pitch == 67 && d.notes[2].durationTick == 240 &&
               d.notes[2].velocity == 96 && d.notes[2].articulation == 5);
    }

    {
        const std::string xml =
            "<?xml version=\"1.0\"?><score-partwise version=\"4.0\">"
            "<part-list/>"
            "<part id=\"P1\"><measure number=\"1\"><attributes><divisions>1</divisions></attributes>"
            "<note><pitch><step>G</step><octave>4</octave></pitch><duration>1</duration><notations><slur type=\"start\"/></notations></note>"
            "</measure></part>"
            "<part id=\"P2\"><measure number=\"1\"><note><pitch><step>D</step><octave>4</octave></pitch><duration>1</duration></note></measure></part>"
            "<part id=\"P3\"><measure number=\"1\"><note><pitch><step>A</step><octave>3</octave></pitch><duration>1</duration><notations><staccato/></notations></note></measure></part>"
            "<part id=\"P4\"><measure number=\"1\"><note><pitch><step>C</step><octave>3</octave></pitch><duration>1</duration></note></measure></part>"
            "</score-partwise>";
        Document d; std::string error;
        assert(importMusicXml(xml, d, error));
        const auto counts = d.sectionCounts();
        assert((counts == std::array<int,4>{{1,1,1,1}}));
        assert(d.notes[0].articulation == 1);
        assert(d.notes[2].articulation == 5);
    }

    {
        Timeline t;
        t.setSelectedPart(0);
        t.pushMidiShort(0x90, 24 + 8, 100, 0, 120.f); // Pizzicato keyswitch C0-B0 range
        t.pushMidiShort(0xB0, 11, 64, 1, 120.f);       // Expression CC11
        t.pushMidiShort(0x90, 72, 100, 2, 120.f);
        const auto events = t.contextFor(0, 32, 0);
        assert(events.size() >= 3);
        assert(t.articulation(0) == 8);
        const auto controls = t.controlsSnapshot();
        assert(controls[0].exp > .49f && controls[0].exp < .52f);
    }

    {
        // 34ch = stereo master + 16 stereo stage feeds. Verify the mixer consumes all feeds stably.
        RenderAudio a{};
        a.sampleRate = 48000; a.frames = 8; a.channels = 34;
        a.interleaved.assign(static_cast<std::size_t>(a.frames) * a.channels, .05f);
        MixerState m{}; m.master = 1.f; m.output = 1.f; m.feed.fill(.25f);
        const auto y = mixToStereo(a, m);
        assert(y.size() == 16);
        for (float v : y) assert(v == v && v >= -1.f && v <= 1.f);
    }

    std::cout << "SONICRAFT v7.0 host QA feature smoke OK\n";
    return 0;
}
