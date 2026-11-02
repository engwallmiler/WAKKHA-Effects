// BEATLIGHT 0.37 — ESP32-WROOM-32, four parallel WS2812B RGB outputs.
// USB is data + ESP32 power ONLY. Use an external 5 V supply for the strip.
#include <Arduino.h>
// IDF4 numbers hardware slots. Each lane reserves two blocks, so slots
// 0/2/4/6 across all eight ESP32 slots provide FOUR parallel workers.
#ifndef FASTLED_RMT_MAX_CHANNELS
#define FASTLED_RMT_MAX_CHANNELS 8
#endif
#ifndef FASTLED_RMT_MEM_BLOCKS
#define FASTLED_RMT_MEM_BLOCKS 2
#endif
#if FASTLED_RMT_MAX_CHANNELS != 8 || FASTLED_RMT_MEM_BLOCKS != 2
#error "WROOM-32 four-output build requires 8 RMT slots and 2 memory blocks per worker."
#endif
#include <FastLED.h>
#include "protocol.h"

#if !defined(CONFIG_IDF_TARGET_ESP32)
#error "Select ESP32 Dev Module / esp32dev (ESP32-WROOM-32). This build is not for S3/C3."
#endif

constexpr uint8_t DATA_PINS[beatlight::OUTPUTS]={18,19,25,26};
constexpr uint32_t USB_BAUD=921600;
constexpr uint32_t WATCHDOG_MS=750;
constexpr uint16_t MAX_MILLIAMPS=20000;
CRGB leds[beatlight::OUTPUTS][beatlight::PIXELS];
CLEDController* controllers[beatlight::OUTPUTS];
uint16_t outputPixels[beatlight::OUTPUTS]={0,0,0,0};
uint16_t frameBytes=0;
beatlight::Parser parser;
uint8_t outgoing[256]; // INFO/ACK only; do not allocate another 3.6 KB frame.
bool configured=false,streaming=false,hasSequence=false;
uint32_t lastFrameAt=0,lastFrameSequence=0;
uint32_t framesShown=0,watchdogTrips=0;

void sendPacket(uint8_t kind,uint32_t seq,const uint8_t* payload,uint16_t length) {
    const size_t size=beatlight::encode(outgoing,kind,seq,payload,length);
    Serial.write(outgoing,size);
}
void acknowledge(uint8_t kind,uint32_t seq,uint8_t result) {
    uint8_t payload[6]={kind,result,0,0,0,0};beatlight::write32(payload+2,millis());
    sendPacket(beatlight::ACK,seq,payload,sizeof(payload));
}
void dark() { FastLED.clear(true);memset(leds,0,sizeof(leds));streaming=false; }
void handlePacket(uint8_t kind,uint32_t seq,const uint8_t* payload,uint16_t length) {
    using namespace beatlight;
    if (kind==HELLO && length==0) {
        dark();configured=false;hasSequence=false;
        const char info[]="{\"device\":\"BEATLIGHT-ESP32\",\"protocol\":2,\"firmware\":\"0.37.0\",\"pixels\":300,\"outputs\":4,\"pins\":[18,19,25,26],\"order\":\"GRB\",\"watchdog_ms\":750}";
        static_assert(sizeof(info)+HEADER+4<=sizeof(outgoing),"INFO packet exceeds output buffer");
        sendPacket(INFO,seq,reinterpret_cast<const uint8_t*>(info),sizeof(info)-1);return;
    }
    if (kind==BLACKOUT && length==0) { dark();acknowledge(kind,seq,RESULT_OK);return; }
    if (kind==CONFIG && length==11 && read16(payload+9)>=500 && read16(payload+9)<=MAX_MILLIAMPS) {
        uint16_t total=0;
        for(uint8_t i=0;i<OUTPUTS;i++) {
            const uint16_t count=read16(payload+i*2);
            if(count>PIXELS) { dark();configured=false;acknowledge(kind,seq,RESULT_INVALID);return; }
            total+=count;
        }
        if(!total) { dark();configured=false;acknowledge(kind,seq,RESULT_INVALID);return; }
        // Clear the OLD full lengths before shortening/disabling any output.
        dark();frameBytes=total*3;
        for(uint8_t i=0;i<OUTPUTS;i++) {
            outputPixels[i]=read16(payload+i*2);
            controllers[i]->setLeds(leds[i],outputPixels[i]?outputPixels[i]:1);
        }
        FastLED.setBrightness(payload[8]);
        // This is a shared budget for ALL four controllers, not per strip.
        FastLED.setMaxPowerInVoltsAndMilliamps(5,read16(payload+9));
        configured=true;hasSequence=false;acknowledge(kind,seq,RESULT_OK);return;
    }
    if (kind==FRAME && (!configured || length==frameBytes)) {
        if (!configured) { acknowledge(kind,seq,RESULT_NOT_CONFIGURED);return; }
        if (hasSequence && seq==lastFrameSequence) { acknowledge(kind,seq,RESULT_OK);return; }
        if (hasSequence && int32_t(seq-lastFrameSequence)<=0) { acknowledge(kind,seq,RESULT_OLD_SEQUENCE);return; }
        // Copy only a complete, CRC-checked RGB frame. GRB is applied at the LED wire.
        uint16_t offset=0;
        for(uint8_t output=0;output<OUTPUTS;output++)for(uint16_t i=0;i<outputPixels[output];i++) {
            leds[output][i]=CRGB(payload[offset],payload[offset+1],payload[offset+2]);offset+=3;
        }
        // One show starts the four RMT controllers together. ACK follows completion.
        FastLED.show();lastFrameAt=millis();streaming=true;
        hasSequence=true;lastFrameSequence=seq;framesShown++;
        acknowledge(kind,seq,RESULT_OK);return;
    }
    // Invalid configuration cannot leave an earlier illuminated frame latched.
    dark();if (kind==CONFIG) configured=false;
    acknowledge(kind,seq,RESULT_INVALID);
}
void setup() {
    Serial.setRxBufferSize(8192);Serial.begin(USB_BAUD);
    controllers[0]=&FastLED.addLeds<WS2812B,18,GRB>(leds[0],beatlight::PIXELS);
    controllers[1]=&FastLED.addLeds<WS2812B,19,GRB>(leds[1],beatlight::PIXELS);
    controllers[2]=&FastLED.addLeds<WS2812B,25,GRB>(leds[2],beatlight::PIXELS);
    controllers[3]=&FastLED.addLeds<WS2812B,26,GRB>(leds[3],beatlight::PIXELS);
    FastLED.setCorrection(UncorrectedColor);FastLED.setDither(0);
    FastLED.setBrightness(64);FastLED.setMaxPowerInVoltsAndMilliamps(5,2000);
    dark();
}
void loop() {
    // Bound a pass so serial noise cannot starve the watchdog.
    for (uint16_t n=0;n<4096 && Serial.available();n++) parser.feed(uint8_t(Serial.read()),millis(),handlePacket);
    parser.expire(millis());
    if (streaming && uint32_t(millis()-lastFrameAt)>=WATCHDOG_MS) { dark();watchdogTrips++; }
    delay(1);
}
