#pragma once
#include <atomic>
#include <cstdint>
#include <limits>

namespace EnhancedM2 {
// Process-local identities, also safe for images created by loader threads.
// Exhaustion permanently returns zero rather than reusing a previous identity.
class ImageLifetimeSequence {
    std::atomic<std::uint64_t> issued;
public:
    explicit ImageLifetimeSequence(std::uint64_t lastIssued = 0) noexcept : issued(lastIssued) {}
    std::uint64_t Next() noexcept {
        auto value = issued.load(std::memory_order_relaxed);
        while (value != std::numeric_limits<std::uint64_t>::max()) {
            if (issued.compare_exchange_weak(value, value + 1, std::memory_order_relaxed))
                return value + 1;
        }
        return 0;
    }
};

inline std::uint64_t NewImageLifetime() noexcept {
    static ImageLifetimeSequence sequence;
    return sequence.Next();
}

inline std::uint64_t NextImageRevision(std::uint64_t current) noexcept {
    return current == 0 || current == std::numeric_limits<std::uint64_t>::max()
        ? 0 : current + 1;
}

// This tracks lifetime and *reported* mutations, not exact pixel continuity.
// Public pixel access in PopLib can bypass BitsChanged. Neither stamp is a
// permission to blend. Per-image mutation follows the existing image ownership
// rules; only the global ID allocator is shared between loader threads.
class ImageIdentity {
    std::uint64_t lifetime = NewImageLifetime();
    std::uint64_t revision = 1;
public:
    ImageIdentity() noexcept = default;
    ImageIdentity(const ImageIdentity&) noexcept : ImageIdentity() {}
    ImageIdentity(ImageIdentity&&) noexcept : ImageIdentity() {}
    ImageIdentity& operator=(const ImageIdentity& other) noexcept {
        if (this != &other) {
            lifetime = NewImageLifetime();
            revision = 1;
        }
        return *this;
    }
    ImageIdentity& operator=(ImageIdentity&& other) noexcept {
        return operator=(static_cast<const ImageIdentity&>(other));
    }
    std::uint64_t Lifetime() const noexcept { return lifetime; }
    std::uint64_t ReportedRevision() const noexcept { return revision; }
    void BitsChanged() noexcept { revision = NextImageRevision(revision); }
};
} // namespace EnhancedM2
