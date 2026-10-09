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
    diag.RenderOffset(&id, 12, 20, 1, 0, 0.3);
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
    std::fclose(invalid);

    std::puts("PASS M2 debug timing, animation and named invalid sprite traces");
}
