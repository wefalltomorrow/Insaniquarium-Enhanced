#include "../ImageIdentity.hpp"
#include <array>
#include <algorithm>
#include <cstdio>
#include <cstdlib>
#include <new>
#include <thread>
#include <utility>
#include <vector>

static void Check(bool ok) { if (!ok) { std::fputs("Image identity test failed\n", stderr); std::exit(1); } }
struct Image {
    EnhancedM2::ImageIdentity identity;
    int width = 10;
    Image() = default;
    // Mirrors the upstream explicit copy constructor, which omits the new field.
    Image(const Image& from) : width(from.width) {}
};
int main() {
    using EnhancedM2::ImageIdentity;
    ImageIdentity first;
    const auto initial = first.Lifetime();
    Check(initial != 0 && first.ReportedRevision() == 1);
    first.BitsChanged(); first.BitsChanged();
    Check(first.Lifetime() == initial && first.ReportedRevision() == 3);
    ImageIdentity copy(first), moved(std::move(first));
    Check(copy.Lifetime() != initial && moved.Lifetime() != initial && copy.Lifetime() != moved.Lifetime());
    Check(copy.ReportedRevision() == 1 && first.Lifetime() == initial);
    const auto oldCopy = copy.Lifetime();
    copy = first;
    Check(copy.Lifetime() != oldCopy && copy.Lifetime() != initial && copy.ReportedRevision() == 1);
    const auto oldMoved = moved.Lifetime();
    moved = std::move(first);
    Check(moved.Lifetime() != oldMoved && moved.Lifetime() != initial);
    first = first; first = std::move(first);
    Check(first.Lifetime() == initial && first.ReportedRevision() == 3);
    Image image, imageCopy(image);
    Check(image.identity.Lifetime() != imageCopy.identity.Lifetime());
    imageCopy = image;
    Check(image.identity.Lifetime() != imageCopy.identity.Lifetime());
    alignas(Image) unsigned char storage[sizeof(Image)];
    Image* sameAddress = new (storage) Image;
    const auto before = sameAddress->identity.Lifetime();
    sameAddress->~Image();
    sameAddress = new (storage) Image;
    Check(sameAddress->identity.Lifetime() != before);
    sameAddress->~Image();
    const auto limit = std::numeric_limits<std::uint64_t>::max();
    EnhancedM2::ImageLifetimeSequence nearLimit(limit - 1);
    Check(nearLimit.Next() == limit && nearLimit.Next() == 0 && nearLimit.Next() == 0);
    Check(EnhancedM2::NextImageRevision(limit) == 0 && EnhancedM2::NextImageRevision(0) == 0);
    Check(EnhancedM2::NextImageRevision(limit - 1) == limit);
    std::array<std::array<std::uint64_t, 512>, 8> ids{};
    std::vector<std::thread> threads;
    for (auto& batch : ids)
        threads.emplace_back([&batch] { for (auto& id : batch) { ImageIdentity stamp; id = stamp.Lifetime(); } });
    for (auto& thread : threads) thread.join();
    std::vector<std::uint64_t> all;
    for (const auto& batch : ids) all.insert(all.end(), batch.begin(), batch.end());
    std::sort(all.begin(), all.end());
    Check(all.front() > 0 && std::adjacent_find(all.begin(), all.end()) == all.end());
    std::puts("PASS image identity construction, copy, assignment, address reuse, revision, exhaustion and concurrent allocation");
}
