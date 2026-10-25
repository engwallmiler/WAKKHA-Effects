#pragma once
#include <stdint.h>
#include <stddef.h>
#include <string.h>

// BLP1 | kind:u8 | reserved=0:u8 | length:u16le | sequence:u32le
// payload[length] | CRC32(header without magic + payload):u32le
namespace beatlight {
constexpr uint16_t PIXELS = 300;
constexpr uint16_t MAX_PAYLOAD = PIXELS * 3;
constexpr size_t HEADER = 12;
constexpr size_t MAX_PACKET = HEADER + MAX_PAYLOAD + 4;
enum Kind : uint8_t { HELLO=1, CONFIG=2, FRAME=3, BLACKOUT=4, INFO=0x81, ACK=0x82 };
enum Result : uint8_t { RESULT_OK=0, RESULT_INVALID=1, RESULT_NOT_CONFIGURED=2, RESULT_OLD_SEQUENCE=3 };
inline uint16_t read16(const uint8_t* p) { return uint16_t(p[0]) | uint16_t(p[1]) << 8; }
inline uint32_t read32(const uint8_t* p) { return uint32_t(p[0]) | uint32_t(p[1]) << 8 | uint32_t(p[2]) << 16 | uint32_t(p[3]) << 24; }
inline void write16(uint8_t* p, uint16_t n) { p[0]=uint8_t(n);p[1]=uint8_t(n>>8); }
inline void write32(uint8_t* p, uint32_t n) { for (uint8_t i=0;i<4;i++) p[i]=uint8_t(n>>(8*i)); }
inline uint32_t crc32(const uint8_t* p, size_t n) {
    uint32_t crc=0xffffffffUL;
    for (size_t i=0;i<n;i++) {
        crc^=p[i];
        for (uint8_t b=0;b<8;b++) crc=(crc>>1) ^ (0xedb88320UL & (0UL-(crc&1UL)));
    }
    return crc ^ 0xffffffffUL;
}
inline size_t encode(uint8_t* out, uint8_t kind, uint32_t seq, const uint8_t* payload, uint16_t length) {
    if (length>MAX_PAYLOAD) return 0;
    memcpy(out,"BLP1",4);out[4]=kind;out[5]=0;write16(out+6,length);write32(out+8,seq);
    if (length) memcpy(out+HEADER,payload,length);
    write32(out+HEADER+length,crc32(out+4,8+length));
    return HEADER+length+4;
}

class Parser {
    uint8_t buffer[MAX_PACKET];
    size_t used=0;
    uint32_t lastByte=0;
    void remove(size_t count) { used-=count;if (used) memmove(buffer,buffer+count,used); }
public:
    uint32_t errors=0;
    void reset() { used=0; }
    void expire(uint32_t now) { if (used && uint32_t(now-lastByte)>100) { used=0;errors++; } }
    template<class Handler> void feed(uint8_t value, uint32_t now, Handler handler) {
        expire(now);lastByte=now;
        buffer[used++]=value;
        while (used>=4) {
            if (memcmp(buffer,"BLP1",4)) { remove(1);continue; }
            if (used<HEADER) return;
            const uint16_t length=read16(buffer+6);
            if (buffer[5]!=0 || length>MAX_PAYLOAD) { errors++;remove(1);continue; }
            const size_t total=HEADER+length+4;
            if (used<total) return;
            if (read32(buffer+HEADER+length)!=crc32(buffer+4,8+length)) { errors++;remove(1);continue; }
            handler(buffer[4],read32(buffer+8),buffer+HEADER,length);
            remove(total);
        }
    }
};
}
