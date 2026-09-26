#include "orchestra_conditioner_v71.h"
#include "orchestra_renderer_v71.h"

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

using namespace Sonicraft::AIStrings;

static void writeU16(std::ofstream& out, std::uint16_t v) {
    const char b[2] = {char(v & 0xFFu), char((v >> 8) & 0xFFu)};
    out.write(b, 2);
}

static void writeU32(std::ofstream& out, std::uint32_t v) {
    const char b[4] = {
        char(v & 0xFFu), char((v >> 8) & 0xFFu),
        char((v >> 16) & 0xFFu), char((v >> 24) & 0xFFu)
    };
    out.write(b, 4);
}

static bool writeWav(
    const std::string& path,
    const std::vector<float>& left,
    const std::vector<float>& right,
    int sampleRate)
{
    if (left.size() != right.size() || left.empty()) return false;
    const std::uint32_t frames = static_cast<std::uint32_t>(left.size());
    const std::uint32_t dataBytes = frames * 2u * 2u;

    std::ofstream out(path, std::ios::binary);
    if (!out) return false;

    out.write("RIFF", 4);
    writeU32(out, 36u + dataBytes);
    out.write("WAVE", 4);
    out.write("fmt ", 4);
    writeU32(out, 16u);
    writeU16(out, 1u);
    writeU16(out, 2u);
    writeU32(out, static_cast<std::uint32_t>(sampleRate));
    writeU32(out, static_cast<std::uint32_t>(sampleRate * 4));
    writeU16(out, 4u);
    writeU16(out, 16u);
    out.write("data", 4);
    writeU32(out, dataBytes);

    for (std::uint32_t i = 0; i < frames; ++i) {
        const auto encode = [](float x) -> std::int16_t {
            const float c = std::clamp(x, -1.f, 1.f);
            return static_cast<std::int16_t>(std::lrint(c * 32767.f));
        };
        const std::int16_t l = encode(left[i]);
        const std::int16_t r = encode(right[i]);
        writeU16(out, static_cast<std::uint16_t>(l));
        writeU16(out, static_cast<std::uint16_t>(r));
    }
    return bool(out);
}

int main(int argc, char** argv) {
    constexpr int sampleRate = 48000;
    constexpr int sustainFrames = sampleRate * 3;
    constexpr int releaseFrames = sampleRate;
    const std::string outPath =
        argc > 1 ? argv[1] : "sonicraft_violin_a4_cleanroom.wav";

    OrchestraConditionerV71 conditioner;
    OrchestraRendererV71 renderer;
    conditioner.reset(sampleRate);
    renderer.reset(sampleRate);

    OrchestraPerformanceState performance{};
    performance.instrument = OrchestraInstrument::Violin;
    performance.tempoBpm = 72.f;
    performance.humanize = .12f;
    performance.smartDynamics = .65f;
    performance.smartArticulation = .75f;

    MusicalControlFrame control{};
    control.midiPitch = 69.f;
    control.velocity = .72f;
    control.dynamics = .65f;
    control.expression = .95f;
    control.vibrato = .42f;
    control.attackCharacter = .44f;
    control.transition = .55f;
    control.articulationBits = kArtSustain;

    OrchestraConditioningFeatures features{};
    if (!conditioner.condition(control, performance, features)) {
        std::cerr << "conditioning failed\n";
        return 2;
    }
    if (!renderer.noteOn(0, 69, control, performance, features)) {
        std::cerr << "renderer noteOn failed\n";
        return 3;
    }

    std::vector<float> left(sustainFrames + releaseFrames, 0.f);
    std::vector<float> right(sustainFrames + releaseFrames, 0.f);
    renderer.render(left.data(), right.data(), sustainFrames, 1.f);
    renderer.noteOff(0, 69);
    renderer.render(
        left.data() + sustainFrames,
        right.data() + sustainFrames,
        releaseFrames,
        1.f);

    double energy = 0.0;
    float peak = 0.f;
    for (std::size_t i = 0; i < left.size(); ++i) {
        energy += double(left[i]) * double(left[i]);
        energy += double(right[i]) * double(right[i]);
        peak = std::max(peak, std::max(std::abs(left[i]), std::abs(right[i])));
    }
    const double rms = std::sqrt(energy / double(left.size() * 2u));
    if (!(rms > 0.001 && rms < 0.5) || !(peak > 0.01f && peak <= 1.f)) {
        std::cerr << "unexpected audio statistics rms=" << rms
                  << " peak=" << peak << "\n";
        return 4;
    }

    if (!writeWav(outPath, left, right, sampleRate)) {
        std::cerr << "failed to write " << outPath << "\n";
        return 5;
    }

    std::cout << "wrote " << outPath
              << " frames=" << left.size()
              << " rms=" << rms
              << " peak=" << peak << "\n";
    return 0;
}
