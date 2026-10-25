#pragma once
#include <stdint.h>
struct CRGB {
    uint8_t r=0,g=0,b=0;
    CRGB()=default;
    CRGB(uint8_t red,uint8_t green,uint8_t blue):r(red),g(green),b(blue) {}
};
struct WS2812B {};
enum EOrder { GRB };
enum ColorCorrection { UncorrectedColor };
struct FakeFastLED {
    CRGB* data=nullptr;int size=0;uint32_t shows=0;uint8_t brightness=0;uint32_t current=0;
    template<class Chip,int Pin,EOrder Order> void addLeds(CRGB* pixels,int count) { data=pixels;size=count; }
    void setCorrection(ColorCorrection) {}
    void setDither(uint8_t) {}
    void setBrightness(uint8_t value) { brightness=value; }
    void setMaxPowerInVoltsAndMilliamps(uint8_t volts,uint32_t ma) { current=ma; }
    void show() { shows++; }
    void clear(bool write) { for(int i=0;i<size;i++)data[i]=CRGB(0,0,0);if(write)show(); }
};
extern FakeFastLED FastLED;
