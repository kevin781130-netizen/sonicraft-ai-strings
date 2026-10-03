#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#include <commctrl.h>
#include <commdlg.h>
#include <algorithm>
#include <array>
#include <cwctype>
#include <iterator>
#include <filesystem>
#include <string>
#include "../../src/score_document_v70.h"

#pragma comment(lib, "comctl32.lib")
#pragma comment(lib, "comdlg32.lib")

namespace {
using Sonicraft::ScoreV70::Document;

enum : int {
    IDC_OPEN = 100, IDC_LIST = 101, IDC_STATUS = 102,
    IDC_PART = 110, IDC_PITCH = 111, IDC_DURATION = 112,
    IDC_VELOCITY = 113, IDC_ART = 114, IDC_APPLY = 115
};

Document gDoc;
std::filesystem::path gPath;
HWND gList = nullptr;
HWND gStatus = nullptr;

const wchar_t* kParts[] = {L"Vln I", L"Vln II", L"Viola", L"Cello"};
const wchar_t* kArts[] = {
    L"Sustain", L"Legato", L"Portamento", L"Expressive Long", L"Marcato", L"Staccato",
    L"Spiccato", L"Tremolo", L"Pizzicato", L"Trill", L"Harmonic", L"Flautando"
};

void setText(HWND h, const std::wstring& s) { SetWindowTextW(h, s.c_str()); }

std::wstring lowerExt(const std::filesystem::path& p) {
    auto s = p.extension().wstring();
    std::transform(s.begin(), s.end(), s.begin(), [](wchar_t c){ return static_cast<wchar_t>(towlower(c)); });
    return s;
}

void updateStatus() {
    const auto c = gDoc.sectionCounts();
    std::wstring s = L"Notes: " + std::to_wstring(gDoc.notes.size()) +
        L"   |   Vln I " + std::to_wstring(c[0]) +
        L"   Vln II " + std::to_wstring(c[1]) +
        L"   Viola " + std::to_wstring(c[2]) +
        L"   Cello " + std::to_wstring(c[3]);
    if (!gPath.empty()) s += L"   |   " + gPath.filename().wstring();
    setText(gStatus, s);
}

void insertColumn(int index, int width, const wchar_t* text) {
    LVCOLUMNW c{};
    c.mask = LVCF_TEXT | LVCF_WIDTH | LVCF_SUBITEM;
    c.cx = width; c.pszText = const_cast<wchar_t*>(text); c.iSubItem = index;
    ListView_InsertColumn(gList, index, &c);
}

void setCell(int row, int col, const std::wstring& value) {
    if (col == 0) {
        LVITEMW item{};
        item.mask = LVIF_TEXT;
        item.iItem = row; item.iSubItem = 0;
        item.pszText = const_cast<wchar_t*>(value.c_str());
        ListView_InsertItem(gList, &item);
    } else {
        ListView_SetItemText(gList, row, col, const_cast<wchar_t*>(value.c_str()));
    }
}

void refreshList(int select = -1) {
    ListView_DeleteAllItems(gList);
    for (std::size_t i = 0; i < gDoc.notes.size(); ++i) {
        const auto& n = gDoc.notes[i];
        const int row = static_cast<int>(i);
        setCell(row, 0, std::to_wstring(i + 1));
        setCell(row, 1, kParts[std::clamp(n.part, 0, 3)]);
        setCell(row, 2, std::to_wstring(n.startTick));
        setCell(row, 3, std::to_wstring(n.durationTick));
        setCell(row, 4, std::to_wstring(n.pitch));
        setCell(row, 5, std::to_wstring(n.velocity));
        setCell(row, 6, kArts[std::clamp(n.articulation, 0, 11)]);
    }
    updateStatus();
    if (select >= 0 && select < static_cast<int>(gDoc.notes.size())) {
        ListView_SetItemState(gList, select, LVIS_SELECTED | LVIS_FOCUSED, LVIS_SELECTED | LVIS_FOCUSED);
        ListView_EnsureVisible(gList, select, FALSE);
    }
}

int selectedRow() {
    return ListView_GetNextItem(gList, -1, LVNI_SELECTED);
}

void loadEditorFields(HWND w, int index) {
    if (index < 0 || index >= static_cast<int>(gDoc.notes.size())) return;
    const auto& n = gDoc.notes[static_cast<std::size_t>(index)];
    SendMessageW(GetDlgItem(w, IDC_PART), CB_SETCURSEL, n.part, 0);
    SetDlgItemInt(w, IDC_PITCH, static_cast<UINT>(n.pitch), FALSE);
    SetDlgItemInt(w, IDC_DURATION, n.durationTick, FALSE);
    SetDlgItemInt(w, IDC_VELOCITY, static_cast<UINT>(n.velocity), FALSE);
    SendMessageW(GetDlgItem(w, IDC_ART), CB_SETCURSEL, n.articulation, 0);
}

bool openScore(HWND owner) {
    wchar_t path[32768]{};
    OPENFILENAMEW ofn{};
    ofn.lStructSize = sizeof(ofn);
    ofn.hwndOwner = owner;
    ofn.lpstrFile = path;
    ofn.nMaxFile = static_cast<DWORD>(std::size(path));
    ofn.lpstrFilter =
        L"MusicXML / MIDI\0*.musicxml;*.xml;*.mid;*.midi\0"
        L"MusicXML\0*.musicxml;*.xml\0"
        L"MIDI\0*.mid;*.midi\0"
        L"All files\0*.*\0";
    ofn.Flags = OFN_FILEMUSTEXIST | OFN_PATHMUSTEXIST | OFN_EXPLORER;
    if (!GetOpenFileNameW(&ofn)) return false;

    Document d;
    std::string error;
    const std::filesystem::path p(path);
    const auto ext = lowerExt(p);
    const bool ok = (ext == L".mid" || ext == L".midi")
        ? Sonicraft::ScoreV70::importMidiFile(p, d, error)
        : Sonicraft::ScoreV70::importMusicXmlFile(p, d, error);
    if (!ok) {
        const std::wstring msg(error.begin(), error.end());
        MessageBoxW(owner, msg.c_str(), L"SONICRAFT Score Editor - Import failed", MB_OK | MB_ICONERROR);
        return false;
    }
    gDoc = std::move(d);
    gPath = p;
    refreshList(gDoc.notes.empty() ? -1 : 0);
    return true;
}

void applyEdit(HWND w) {
    const int row = selectedRow();
    if (row < 0) {
        MessageBoxW(w, L"Select a note first.", L"SONICRAFT Score Editor", MB_OK | MB_ICONINFORMATION);
        return;
    }
    BOOL okPitch=FALSE, okDur=FALSE, okVel=FALSE;
    const UINT pitch = GetDlgItemInt(w, IDC_PITCH, &okPitch, FALSE);
    const UINT duration = GetDlgItemInt(w, IDC_DURATION, &okDur, FALSE);
    const UINT velocity = GetDlgItemInt(w, IDC_VELOCITY, &okVel, FALSE);
    const int part = static_cast<int>(SendMessageW(GetDlgItem(w, IDC_PART), CB_GETCURSEL, 0, 0));
    const int art = static_cast<int>(SendMessageW(GetDlgItem(w, IDC_ART), CB_GETCURSEL, 0, 0));
    if (!okPitch || !okDur || !okVel ||
        !gDoc.edit(static_cast<std::size_t>(row), part, static_cast<int>(pitch), duration,
                   static_cast<int>(velocity), art)) {
        MessageBoxW(w, L"Invalid edit. Pitch 0-127, duration > 0, velocity 1-127.", L"SONICRAFT Score Editor", MB_OK | MB_ICONWARNING);
        return;
    }
    refreshList(row);
}

HWND add(HWND p, const wchar_t* cls, const wchar_t* text, DWORD style,
         int x, int y, int width, int height, int id) {
    return CreateWindowExW(0, cls, text, WS_CHILD | WS_VISIBLE | style,
                           x, y, width, height, p, reinterpret_cast<HMENU>(static_cast<INT_PTR>(id)),
                           GetModuleHandleW(nullptr), nullptr);
}

void buildUi(HWND w) {
    add(w, L"STATIC", L"SONICRAFT AI Strings Q4 - Score Editor", SS_LEFT, 18, 14, 520, 28, -1);
    add(w, L"BUTTON", L"Import MusicXML / MIDI", BS_PUSHBUTTON, 820, 12, 220, 30, IDC_OPEN);
    gStatus = add(w, L"STATIC", L"No score loaded.", SS_LEFT, 18, 48, 1020, 24, IDC_STATUS);

    gList = add(w, WC_LISTVIEWW, L"", LVS_REPORT | LVS_SINGLESEL | LVS_SHOWSELALWAYS | WS_BORDER,
                18, 82, 1022, 430, IDC_LIST);
    ListView_SetExtendedListViewStyle(gList, LVS_EX_FULLROWSELECT | LVS_EX_GRIDLINES | LVS_EX_DOUBLEBUFFER);
    insertColumn(0, 52, L"#");
    insertColumn(1, 100, L"Section");
    insertColumn(2, 120, L"Start tick");
    insertColumn(3, 120, L"Duration");
    insertColumn(4, 80, L"Pitch");
    insertColumn(5, 90, L"Velocity");
    insertColumn(6, 200, L"Articulation");

    add(w, L"STATIC", L"Selected note", SS_LEFT, 18, 528, 120, 20, -1);
    add(w, L"STATIC", L"Section", SS_LEFT, 18, 558, 70, 20, -1);
    HWND part = add(w, WC_COMBOBOXW, L"", CBS_DROPDOWNLIST, 88, 554, 150, 220, IDC_PART);
    for (const auto* s : kParts) SendMessageW(part, CB_ADDSTRING, 0, reinterpret_cast<LPARAM>(s));

    add(w, L"STATIC", L"Pitch", SS_LEFT, 260, 558, 50, 20, -1);
    add(w, L"EDIT", L"60", ES_NUMBER | WS_BORDER, 310, 554, 70, 24, IDC_PITCH);
    add(w, L"STATIC", L"Duration", SS_LEFT, 402, 558, 70, 20, -1);
    add(w, L"EDIT", L"480", ES_NUMBER | WS_BORDER, 474, 554, 90, 24, IDC_DURATION);
    add(w, L"STATIC", L"Velocity", SS_LEFT, 586, 558, 70, 20, -1);
    add(w, L"EDIT", L"90", ES_NUMBER | WS_BORDER, 654, 554, 70, 24, IDC_VELOCITY);

    add(w, L"STATIC", L"Articulation", SS_LEFT, 18, 598, 90, 20, -1);
    HWND art = add(w, WC_COMBOBOXW, L"", CBS_DROPDOWNLIST, 108, 594, 230, 260, IDC_ART);
    for (const auto* s : kArts) SendMessageW(art, CB_ADDSTRING, 0, reinterpret_cast<LPARAM>(s));
    add(w, L"BUTTON", L"Apply note edit", BS_PUSHBUTTON, 820, 590, 220, 32, IDC_APPLY);

    add(w, L"STATIC",
        L"Import assigns MIDI channels / MusicXML parts to Vln I, Vln II, Viola and Cello. Edits are held in this score session for QA and rendering integration.",
        SS_LEFT, 18, 640, 1020, 36, -1);
}

LRESULT CALLBACK wndProc(HWND w, UINT msg, WPARAM wp, LPARAM lp) {
    switch (msg) {
        case WM_CREATE:
            buildUi(w);
            return 0;
        case WM_COMMAND:
            if (LOWORD(wp) == IDC_OPEN) openScore(w);
            else if (LOWORD(wp) == IDC_APPLY) applyEdit(w);
            return 0;
        case WM_NOTIFY: {
            const auto* h = reinterpret_cast<NMHDR*>(lp);
            if (h && h->idFrom == IDC_LIST && h->code == LVN_ITEMCHANGED) {
                const auto* n = reinterpret_cast<NMLISTVIEW*>(lp);
                if ((n->uNewState & LVIS_SELECTED) != 0) loadEditorFields(w, n->iItem);
            }
            return 0;
        }
        case WM_DESTROY:
            PostQuitMessage(0);
            return 0;
        default:
            return DefWindowProcW(w, msg, wp, lp);
    }
}
} // namespace

int WINAPI wWinMain(HINSTANCE instance, HINSTANCE, LPWSTR, int show) {
    INITCOMMONCONTROLSEX ic{sizeof(ic), ICC_LISTVIEW_CLASSES | ICC_STANDARD_CLASSES};
    InitCommonControlsEx(&ic);

    WNDCLASSW wc{};
    wc.lpfnWndProc = wndProc;
    wc.hInstance = instance;
    wc.lpszClassName = L"SonicraftScoreEditorV70";
    wc.hCursor = LoadCursorW(nullptr, IDC_ARROW);
    wc.hbrBackground = reinterpret_cast<HBRUSH>(COLOR_WINDOW + 1);
    RegisterClassW(&wc);

    HWND w = CreateWindowExW(0, wc.lpszClassName, L"SONICRAFT AI Strings Q4 - Score Editor",
                             WS_OVERLAPPED | WS_CAPTION | WS_SYSMENU | WS_MINIMIZEBOX,
                             CW_USEDEFAULT, CW_USEDEFAULT, 1080, 730,
                             nullptr, nullptr, instance, nullptr);
    if (!w) return 2;
    ShowWindow(w, show);
    UpdateWindow(w);

    MSG m{};
    while (GetMessageW(&m, nullptr, 0, 0) > 0) {
        TranslateMessage(&m);
        DispatchMessageW(&m);
    }
    return static_cast<int>(m.wParam);
}
#endif
