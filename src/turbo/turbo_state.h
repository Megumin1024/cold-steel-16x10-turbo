#pragma once
#include <cstdint>

// 只有原生加速查询更新按下沿；其他输入不能改变加速开关。
struct TurboState {
    bool active = false;
    bool held_before = false;
    bool Update(bool held) {
        if (held && !held_before) active = !active;
        held_before = held;
        return active;
    }
    std::uint8_t Route(std::uintptr_t caller, std::uint8_t original) {
        if (caller == 0x00483012) return Update(original != 0) ? 1 : 0;
        if (caller == 0x004d7c5f || caller == 0x004f224d) return active ? 1 : 0;
        return original;
    }
};

