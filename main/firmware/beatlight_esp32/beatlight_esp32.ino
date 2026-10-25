// BEATLIGHT 0.22 — ESP32 DevKit / WROOM-32, one WS2812B RGB strip, 300 LEDs.
// USB is data + ESP32 power ONLY. Use an external 5 V supply for the strip.
#include <Arduino.h>
#include <FastLED.h>
#include "protocol.h"

#if !defined(CONFIG_IDF_TARGET_ESP32)
#error "Select ESP32 Dev Module / esp32dev (ESP32-WROOM-32). This build is not for S3/C3."
#endif

constexpr uint8_t DATA_PIN=18;
constexpr uint32_t USB_BAUD=921600;
constexpr uint32_t WATCHDOG_MS=750;
constexpr uint16_t MAX_MILLIAMPS=20000;
CRGB leds[beatlight::PIXELS];
beatlight::Parser parser;
uint8_t outgoing[beatlight::MAX_PACKET];
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
void dark() { FastLED.clear(true);streaming=false; }
void handlePacket(uint8_t kind,uint32_t seq,const uint8_t* payload,uint16_t length) {
    using namespace beatlight;
    if (kind==HELLO && length==0) {
        dark();configured=false;hasSequence=false;
        const char info[]="{\"device\":\"BEATLIGHT-ESP32\",\"protocol\":1,\"firmware\":\"0.22.0\",\"pixels\":300,\"pin\":18,\"order\":\"GRB\",\"watchdog_ms\":750}";
        sendPacket(INFO,seq,reinterpret_cast<const uint8_t*>(info),sizeof(info)-1);return;
    }
    if (kind==BLACKOUT && length==0) { dark();acknowledge(kind,seq,RESULT_OK);return; }
    if (kind==CONFIG && length==5 && read16(payload)==PIXELS && read16(payload+3)>=500 && read16(payload+3)<=MAX_MILLIAMPS) {
        dark();FastLED.setBrightness(payload[2]);
        FastLED.setMaxPowerInVoltsAndMilliamps(5,read16(payload+3));
        configured=true;hasSequence=false;acknowledge(kind,seq,RESULT_OK);return;
    }
    if (kind==FRAME && length==PIXELS*3) {
        if (!configured) { acknowledge(kind,seq,RESULT_NOT_CONFIGURED);return; }
        if (hasSequence && seq==lastFrameSequence) { acknowledge(kind,seq,RESULT_OK);return; }
        if (hasSequence && int32_t(seq-lastFrameSequence)<=0) { acknowledge(kind,seq,RESULT_OLD_SEQUENCE);return; }
        // Copy only a complete, CRC-checked RGB frame. GRB is applied at the LED wire.
        for (uint16_t i=0;i<PIXELS;i++) leds[i]=CRGB(payload[i*3],payload[i*3+1],payload[i*3+2]);
        FastLED.show();lastFrameAt=millis();streaming=true;
        hasSequence=true;lastFrameSequence=seq;framesShown++;
        acknowledge(kind,seq,RESULT_OK);return;
    }
    // Invalid configuration cannot leave an earlier illuminated frame latched.
    dark();if (kind==CONFIG) configured=false;
    acknowledge(kind,seq,RESULT_INVALID);
}
void setup() {
    Serial.setRxBufferSize(2048);Serial.begin(USB_BAUD);
    FastLED.addLeds<WS2812B,DATA_PIN,GRB>(leds,beatlight::PIXELS);
    FastLED.setCorrection(UncorrectedColor);FastLED.setDither(0);
    FastLED.setBrightness(64);FastLED.setMaxPowerInVoltsAndMilliamps(5,2000);
    dark();
}
void loop() {
    // Bound a pass so serial noise cannot starve the watchdog.
    for (uint16_t n=0;n<2048 && Serial.available();n++) parser.feed(uint8_t(Serial.read()),millis(),handlePacket);
    parser.expire(millis());
    if (streaming && uint32_t(millis()-lastFrameAt)>=WATCHDOG_MS) { dark();watchdogTrips++; }
    delay(1);
}
