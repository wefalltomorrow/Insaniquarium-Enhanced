#include "../DebugTrace.hpp"
#include <cstdio>
#include <cstdlib>
#include <cstring>

static void Verify(bool condition, const char* what) {
    if (!condition) {
        std::fprintf(stderr, "FAIL: %s\n", what);
        std::exit(1);
    }
}

int main() {
#ifdef _WIN32
    _putenv_s("INSANIQUARIUM_M2_DEBUG", "1");
#else
    setenv("INSANIQUARIUM_M2_DEBUG", "1", 1);
#endif
    auto& diag = M2Debug::Get();
    Verify(diag.Active(), "debug opt-in");
    diag.Begin(16.67, 0.3, 1);
    diag.SimTick();
    diag.Updated(M2Debug::Fish);
    const int id = 7;
    diag.Drawn(M2Debug::Fish, &id, 12, 20, 3);
    diag.SpriteCel(&id, 1, 0, 12, 20, 8, 8, 256, 256, "images/test_sheet.png");
    diag.SpriteCel(&id, -1, 0, 12, 20, 8, 8, 256, 256, "images/test_sheet.png");
    diag.SpriteCel(&id, -1, 0, 139, 196, 3, 1, 165, 25, "images/merylblink");
    diag.SpriteCel(&id, -1, 0, 0, 0, 5, 1, 150, 30, "images/chomp");
    diag.SpriteCel(&id, -1, 0, 0, 0, 20, 1, 300, 30, "images/smoketiny");
    diag.SpriteCel(&id, -1, 0, 0, 0, 20, 1, 300, 30, "images/explosion");
    diag.SpriteCel(&id, 11, 0, 0, 0, 10, 6, 800, 480, "images/lasers");
    diag.SpriteCel(&id, 13, 5, 0, 0, 10, 6, 800, 480, "images/lasers");
    diag.SpriteCel(&id, 14, 0, 0, 0, 10, 6, 800, 480, "images/lasers");
    diag.SpriteCel(&id, 0, 1, 0, 0, 10, 1, 1000, 100, "images/eggcrack2");
    diag.SpriteCel(&id, 8, 0, 0, 0, 8, 1, 240, 30, "images/unknown.png");
    diag.RenderOffset(&id, 12, 20, 1, 0, 0.3);
    diag.UnsafeFishPosition(&id, -5.653851e214, 20.0);
    diag.UnsafeFishPosition(&id, -5.653851e214, 20.0);
    diag.End(1, true, true, 16.67, 1.05, 0.3);
    diag.Begin(16.67, 0.8, 0);
    diag.Drawn(M2Debug::Fish, &id, 12, 20, 3);
    diag.End(0, true, true, 16.67, 1.05, 0.8);
    diag.WindowTitle(35.7, 59.9);
    Verify(std::strstr(diag.Title(), "35.7") != nullptr, "titlebar statistics");

    std::fflush(nullptr); // flush recorder streams before inspecting files
    FILE* csv = std::fopen("M2DebugFrames.csv", "rb");
    Verify(csv != nullptr, "frames output exists");
    int lines = 0, c = 0;
    while ((c = std::fgetc(csv)) != EOF) if (c == '\n') ++lines;
    std::fclose(csv);
    Verify(lines >= 3, "two diagnostics frame rows");

    FILE* obj = std::fopen("M2DebugObjects.csv", "rb");
    Verify(obj != nullptr, "object tracing output exists");
    std::fclose(obj);

    FILE* interp = std::fopen("M2DebugInterpolation.csv", "rb");
    Verify(interp != nullptr, "interpolation output exists");
    std::fclose(interp);

    FILE* invalid = std::fopen("M2DebugInvalidSprites.csv", "rb");
    Verify(invalid != nullptr, "invalid sprite details file exists");
    char record[512] = {};
    Verify(std::fgets(record, sizeof(record), invalid) != nullptr, "invalid file CSV header");
    Verify(std::fgets(record, sizeof(record), invalid) != nullptr, "invalid file CSV data");
    Verify(std::strstr(record, "images/test_sheet.png") != nullptr, "asset path appears in invalid sprite trace");
    Verify(std::strstr(record, ",-1,0,12,20") != nullptr, "invalid cel numbers appear in trace");
    int unexpectedRows = 1;
    while (std::fgets(record, sizeof(record), invalid) != nullptr) {
        Verify(std::strstr(record, "merylblink") == nullptr &&
               std::strstr(record, "chomp") == nullptr,
               "known hidden frames must not count as invalid");
        ++unexpectedRows;
    }
    Verify(unexpectedRows == 4, "unclassified negative, high, laser-14 and egg row cells all logged");
    std::fclose(invalid);

    FILE* skipped = std::fopen("M2DebugSkippedSprites.csv", "rb");
    Verify(skipped != nullptr, "hidden-sprite output exists");
    Verify(std::fgets(record, sizeof(record), skipped) != nullptr,
           "skipped header exists");
    Verify(std::fgets(record, sizeof(record), skipped) != nullptr &&
           std::strstr(record, "images/merylblink") != nullptr,
           "Meryl intentional no-draw frame logged");
    Verify(std::fgets(record, sizeof(record), skipped) != nullptr &&
           std::strstr(record, "images/chomp") != nullptr,
           "Chomp intentional no-draw frame logged");
    Verify(std::fgets(record, sizeof(record), skipped) != nullptr &&
           std::strstr(record, "images/smoketiny") != nullptr,
           "Smoke first hidden frame logged");
    Verify(std::fgets(record, sizeof(record), skipped) != nullptr &&
           std::strstr(record, "images/explosion") != nullptr,
           "Explosion first hidden frame logged");
    Verify(std::fgets(record, sizeof(record), skipped) != nullptr &&
           std::strstr(record, "images/lasers") != nullptr &&
           std::strstr(record, ",11,0,") != nullptr,
           "Laser first out-of-sheet tail column logged");
    Verify(std::fgets(record, sizeof(record), skipped) != nullptr &&
           std::strstr(record, "images/lasers") != nullptr &&
           std::strstr(record, ",13,5,") != nullptr,
           "Laser tail at highest real row logged");
    Verify(std::fgets(record, sizeof(record), skipped) == nullptr,
           "only the known nonrendering frames are classified");
    std::fclose(skipped);

    std::puts("PASS M2 debug timing, classified hidden frames and invalid sprite traces");
}
