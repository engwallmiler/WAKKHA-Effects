#pragma once
#include <stdint.h>
#include <stddef.h>
#include <deque>
#include <vector>
extern uint32_t clockMs;
inline uint32_t millis() { return clockMs; }
inline void delay(uint32_t n) { clockMs+=n; }
struct FakeSerial {
    std::deque<uint8_t> input;
    std::vector<uint8_t> output;
    uint32_t baud=0;size_t rx=0;
    void setRxBufferSize(size_t n) { rx=n; }
    void begin(uint32_t value) { baud=value; }
    size_t available() { return input.size(); }
    int read() { uint8_t v=input.front();input.pop_front();return v; }
    size_t write(const uint8_t* data,size_t size) { output.insert(output.end(),data,data+size);return size; }
};
extern FakeSerial Serial;
