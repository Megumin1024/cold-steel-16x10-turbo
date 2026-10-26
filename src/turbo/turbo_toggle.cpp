#include "shared/code_check.h"
#include "shared/mod_api.h"
#include "turbo_state.h"
#include <intrin.h>
#pragma intrinsic(_ReturnAddress)

namespace {
const AtmtModApi* g_api = nullptr;
LONG g_started = 0;
int32_t g_enabled = 1;
TurboState g_state;
constexpr uintptr_t kQuery = 0x0040db7a;
using QueryFn = uint8_t(__fastcall*)(void*, void*, int32_t, int32_t, int32_t);
QueryFn g_original = nullptr;

// thiscall 以 ECX 传入对象，三个参数由被调用方清理，返回值使用 AL。
__declspec(noinline) uint8_t __fastcall QueryDetour(
    void* self, void* edx, int32_t button, int32_t kind, int32_t directional) {
    const uintptr_t caller = reinterpret_cast<uintptr_t>(_ReturnAddress());
    const uint8_t original = g_original(self, edx, button, kind, directional);
    if (button != 7) return original;
    const bool before = g_state.active;
    const uint8_t result = g_state.Route(caller, original);
    if (caller == 0x00483012 && before != g_state.active && g_api->log) {
        g_api->log(g_state.active ? "turbo_toggle: 加速已开启" : "turbo_toggle: 加速已关闭");
    }
    return result;
}
}
extern "C" {
__declspec(dllexport) uint32_t __cdecl AtmtModInit(const AtmtModApi* api) {
    if (!api || api->version < ATMT_MOD_API_VERSION) return 0;
    if (InterlockedCompareExchange(&g_started, 1, 0) != 0) return 0;
    g_api = api;
    static const AtmtSetting settings[] = {
        {ATMT_SETTING_BOOL, ATMT_SETTING_RESTART, "General", "Enabled",
         "加速按键切换", "按一次开启、再按一次关闭；沿用原键位和倍率，重启游戏后生效", &g_enabled}
    };
    api->settings_register(api, "加速切换", settings, 1);
    if (!g_enabled) return ATMT_MOD_API_VERSION;
    static const atmt_code::Expect expected[] = {
        {kQuery, "\xe9\xc1\x86\x03\x00", 5, "输入跳板"},
        {0x00446240, "\x55\x8b\xec\x53\x8b\x5d\x08\x56", 8, "原生输入入口"},
        {0x00483006, "\x53\x6a\x00\x6a\x07\x8b\xc8\xe8\x68\xab\xf8\xff", 12, "加速开关输入"},
        {0x004d7c54, "\x6a\x01\x6a\x00\x6a\x07\xe8\x1b\x5f\xf3\xff", 11, "战斗动画跳过输入"},
        {0x004f2242, "\x6a\x01\x6a\x00\x6a\x07\xe8\x2d\xb9\xf1\xff", 11, "战斗结算跳过输入"}
    };
    char reason[256];
    if (!atmt_code::CheckAll(expected, reason, sizeof(reason))) {
        if (api->log_error) api->log_error(reason);
        return ATMT_MOD_API_VERSION;
    }
    void* hook = api->hook_create(reinterpret_cast<void*>(kQuery),
                                  reinterpret_cast<void*>(&QueryDetour),
                                  reinterpret_cast<void**>(&g_original));
    if (!hook || api->hook_enable(hook) != 0) {
        if (hook) api->hook_remove(hook);
        if (api->log_error) api->log_error("turbo_toggle: 输入钩子安装失败，未启用加速切换");
        return ATMT_MOD_API_VERSION;
    }
    if (api->log) api->log("turbo_toggle: 五处代码校验通过；单击切换已启用；原始按键和倍率保持不变");
    return ATMT_MOD_API_VERSION;
}
__declspec(dllexport) void __cdecl AtmtModShutdown() {}
__declspec(dllexport) const char* __cdecl AtmtModDescription() {
    return "加速键按一下开启，再按一下关闭；长按不重复切换。";
}
}

