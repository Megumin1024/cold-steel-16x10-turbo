#include "turbo_state.h"
#include <cassert>
#include <cstdio>
int main() {
    TurboState s;
    assert(s.Route(0x483012,0)==0);
    assert(s.Route(0x483012,1)==1);
    for(int i=0;i<100000;++i) assert(s.Route(0x483012,1)==1);
    assert(s.Route(0x483012,0)==1);
    assert(s.Route(0x4d7c5f,0)==1);
    assert(s.Route(0x4f224d,0)==1);
    assert(s.Route(0x123456,0)==0);
    assert(s.Route(0x123456,2)==2);
    assert(s.Route(0x483012,1)==0);
    for(int i=0;i<1000;++i) assert(s.Route(0x483012,1)==0);
    assert(s.Route(0x4d7c5f,1)==0);
    assert(s.Route(0x4f224d,1)==0);
    assert(s.Route(0x483012,0)==0);
    assert(s.Route(0x483012,2)==1);
    assert(s.Route(0x483012,0)==1);
    assert(s.Route(0x483012,1)==0);
    std::puts("开启、松开保持、长按防重复、再次关闭、跳过同步和无关输入测试通过");
}

