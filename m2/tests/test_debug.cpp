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
    // Regression coverage for long-session trace sampling; no changes
    // to sprite warnings, per-frame counters or simulation are permitted.
    Verify(M2Debug::Recorder::SampleDetailFrame(0), "first frame traced");
    Verify(M2Debug::Recorder::SampleDetailFrame(9999), "initial full-detail window");
    Verify(!M2Debug::Recorder::SampleDetailFrame(10000), "late unsampled frame");
    Verify(!M2Debug::Recorder::SampleDetailFrame(10001), "late adjacent frame");
    Verify(M2Debug::Recorder::SampleDetailFrame(10002), "late sampled frame");
    Verify(M2Debug::Recorder::SampleDetailFrame(30000), "long session still sampled");
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
    diag.SpriteCel(&id, 0, 1, 20, 0, 17, 1, 1020, 220, "images/warphole");
    diag.SpriteCel(&id, 0, 1, 0, 0, 17, 1, 1700, 220, "images/warpglow");
    diag.SpriteCel(&id, 0, 1, 0, 0, 10, 1, 1180, 145, "images/eggcrack2");
    diag.SpriteCel(&id, 0, 2, 0, 0, 17, 1, 1020, 220, "images/warphole");
    diag.SpriteCel(&id, 0, 1, 0, 0, 16, 1, 1020, 220, "images/warphole");
    diag.SpriteCel(&id, 1, 1, 0, 0, 10, 1, 1180, 145, "images/eggcrack2");
    diag.SpriteCel(&id, 0, 1, 0, 0, 10, 1, 1180, 145, "images/eggcrack1");
    diag.SpriteCel(&id, 8, 0, 0, 0, 8, 1, 240, 30, "images/unknown.png");
    diag.Updated(M2Debug::OtherPet);
    diag.Updated(M2Debug::Missile);
    diag.Updated(M2Debug::ShotEffect);
    int shotX = 20, shotY = 30, shotAnim = 2;
    {
        M2Debug::IntDrawGuard shot(M2Debug::ShotEffect, &id, shotX, shotY, shotAnim);
        Verify(shotX == 20 && shotY == 30, "shot instrumentation must not move object");
    }
    diag.Drawn(M2Debug::OtherPet, &id, 12, 20, 1);
    diag.Drawn(M2Debug::Missile, &id, 12, 20, 3);
    diag.RenderOffset(&id, 12, 20, 1, 0, 0.3);
    diag.ObjectMotion(M2Debug::Coin, &id, 120, 50, -1, 0, 0.3, false, true);
    diag.ObjectMotion(M2Debug::Food, &id, 123, 44, 0, -1, 0.5, false, true);
    diag.ObjectMotion(M2Debug::Food, &id, 123, 44, 0, 0, 0.5, true, false);
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
    char frameHeader[1024] = {};
    Verify(std::fgets(frameHeader, sizeof(frameHeader), csv) != nullptr,
           "frame CSV header exists");
    Verify(std::strstr(frameHeader, "updatesOtherPet") != nullptr &&
           std::strstr(frameHeader, "drawsMissile") != nullptr &&
           std::strstr(frameHeader, "drawsShotEffect") != nullptr,
           "additional object counts exist in frame CSV");
    std::rewind(csv); // Include the header in the existing line-count assertion.
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

    char motionLine[512] = {};
    FILE* motion = std::fopen("M2DebugObjectMotion.csv", "rb");
    Verify(motion != nullptr, "coin/food motion output exists");
    Verify(std::fgets(motionLine, sizeof(motionLine), motion) != nullptr &&
           std::strstr(motionLine, "kind,objectId") != nullptr, "motion CSV schema");
    Verify(std::fgets(motionLine, sizeof(motionLine), motion) != nullptr &&
           std::strstr(motionLine, ",coin,") != nullptr &&
           std::strstr(motionLine, ",-1,0,") != nullptr, "coin interpolation logged");
    Verify(std::fgets(motionLine, sizeof(motionLine), motion) != nullptr &&
           std::strstr(motionLine, ",food,") != nullptr &&
           std::strstr(motionLine, ",0,-1,") != nullptr, "food interpolation logged");
    Verify(std::fgets(motionLine, sizeof(motionLine), motion) != nullptr &&
           std::strstr(motionLine, ",food,") != nullptr &&
           std::strstr(motionLine, ",1,0") != nullptr, "paused food with reset history");
    Verify(std::fgets(motionLine, sizeof(motionLine), motion) == nullptr,
           "only tracked coin/food motions emitted");
    std::fclose(motion);
    FILE* invalid = std::fopen("M2DebugInvalidSprites.csv", "rb");
    Verify(invalid != nullptr, "invalid sprite details file exists");
    char record[512] = {};
    Verify(std::fgets(record, sizeof(record), invalid) != nullptr, "invalid file CSV header");
    Verify(std::fgets(record, sizeof(record), invalid) != nullptr, "invalid file CSV data");
    Verify(std::strstr(record, "images/test_sheet.png") != nullptr, "asset path appears in invalid sprite trace");
    Verify(std::strstr(record, ",-1,0,12,20") != nullptr, "invalid cel numbers appear in trace");
    int unexpectedRows = 1;
    bool rejectedWarp = false, rejectedEgg = false;
    while (std::fgets(record, sizeof(record), invalid) != nullptr) {
        if (std::strstr(record, "images/warphole")) rejectedWarp = true;
        if (std::strstr(record, "images/eggcrack")) rejectedEgg = true;
        Verify(std::strstr(record, "merylblink") == nullptr &&
               std::strstr(record, "chomp") == nullptr,
               "known hidden frames must not count as invalid");
        ++unexpectedRows;
    }
    Verify(unexpectedRows == 7, "seven invalid cells remain, including boundary near misses");
    Verify(rejectedWarp && rejectedEgg, "unknown warp and egg requests remain invalid");
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
    Verify(std::fgets(record, sizeof(record), skipped) != nullptr &&
           std::strstr(record, "images/warphole") != nullptr &&
           std::strstr(record, ",0,1,") != nullptr, "exact warphole tail");
    Verify(std::fgets(record, sizeof(record), skipped) != nullptr &&
           std::strstr(record, "images/warpglow") != nullptr &&
           std::strstr(record, ",0,1,") != nullptr, "exact warpglow tail");
    Verify(std::fgets(record, sizeof(record), skipped) != nullptr &&
           std::strstr(record, "images/eggcrack2") != nullptr &&
           std::strstr(record, ",0,1,") != nullptr, "exact egg crack tail");
    Verify(std::fgets(record, sizeof(record), skipped) == nullptr,
           "only known nonrendering frames are classified");
    std::fclose(skipped);

    std::puts("PASS M2 debug timing, classified hidden frames and invalid sprite traces");
}
