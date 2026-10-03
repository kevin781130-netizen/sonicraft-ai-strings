#pragma once
#include "vstgui/vstgui.h"
#include <cstdint>
#include <string>

namespace Sonicraft::AIStrings {

class Controller;

class ScoreEditorViewV70 final : public VSTGUI::CView {
public:
    explicit ScoreEditorViewV70(const VSTGUI::CRect& size, Controller* controller);
    ~ScoreEditorViewV70() noexcept override;

    void draw(VSTGUI::CDrawContext* context) override;
    VSTGUI::CMouseEventResult onMouseDown(VSTGUI::CPoint& where, const VSTGUI::CButtonState& buttons) override;
    VSTGUI::CMouseEventResult onMouseMoved(VSTGUI::CPoint& where, const VSTGUI::CButtonState& buttons) override;
    VSTGUI::CMouseEventResult onMouseUp(VSTGUI::CPoint& where, const VSTGUI::CButtonState& buttons) override;
    int32_t onKeyDown(VSTGUI::VstKeyCode& keyCode) override;

private:
    enum class Tool { Select, Draw, Erase };
    enum class DragMode { None, Move, Resize, Velocity };

    struct Layout {
        VSTGUI::CRect all;
        VSTGUI::CRect toolbar;
        VSTGUI::CRect piano;
        VSTGUI::CRect articulation;
        VSTGUI::CRect inspector;
    };

    Controller* controller_ = nullptr;
    Tool tool_ = Tool::Select;
    DragMode dragMode_ = DragMode::None;
    int selected_ = -1;
    int activePart_ = 0;
    int snapDivision_ = 4; // quarter / 4 = sixteenth-note grid
    double scrollQuarter_ = 0.0;
    double beatWidth_ = 52.0;
    VSTGUI::CPoint dragStart_{};
    std::uint32_t dragOrigStart_ = 0;
    std::uint32_t dragOrigDuration_ = 1;
    int dragOrigPitch_ = 60;
    int dragOrigVelocity_ = 90;
    std::string status_{"VST3 piano roll ready"};

    Layout layout() const;
    int ppq() const noexcept;
    std::uint32_t snapTick(std::int64_t tick) const noexcept;
    int controllerActivePart() const noexcept;
    void setActivePart(int part);
    void syncSelectedToHost();
    void importScore();
    void invalidateSelf();
    void ensureSelectionValid();

    VSTGUI::CRect toolRect(int index) const;
    VSTGUI::CRect partRect(int part) const;
    VSTGUI::CRect navRect(int index) const;
    VSTGUI::CRect snapRect() const;
    VSTGUI::CRect noteRect(std::size_t index) const;
    VSTGUI::CRect velocityRect() const;
    VSTGUI::CRect deleteRect() const;
    VSTGUI::CRect articulationRect(int articulation) const;

    int hitNote(const VSTGUI::CPoint& where, bool* onResizeEdge = nullptr) const;
    int pitchAt(const VSTGUI::CPoint& where) const noexcept;
    std::uint32_t tickAt(const VSTGUI::CPoint& where) const noexcept;
    void addNoteAt(const VSTGUI::CPoint& where);
    void eraseSelected();
    void setSelectedArticulation(int articulation);
    void setSelectedVelocityFromX(double x);

    static const char* partName(int part) noexcept;
    static const char* articulationShort(int articulation) noexcept;
    static std::string pitchName(int midi);
};

} // namespace Sonicraft::AIStrings
