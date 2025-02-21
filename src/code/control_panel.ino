//код для пульта управления 
#include <Adafruit_NeoPixel.h>

#define BUTTON_UP 4
#define BUTTON_DOWN 11
#define LED_COUNT 2
#define LED_PIN 6
#define BRIGHTNESS 25


Adafruit_NeoPixel strip(LED_COUNT, LED_PIN, NEO_GRBW + NEO_KHZ800);

void setup() {
  Serial.begin(9600);
  pinMode(BUTTON_UP, INPUT_PULLUP);
  pinMode(BUTTON_DOWN, INPUT_PULLUP);
  strip.begin();           
  strip.show();            
  strip.setBrightness(BRIGHTNESS);


}

void loop() {
  if (digitalRead(BUTTON_UP) == digitalRead(BUTTON_DOWN)){
    strip.setPixelColor(0, strip.Color(0, 0, 0));
    strip.show();
  }
  else{
    if (digitalRead(BUTTON_UP) == LOW){
      Serial.write(1);
      delay(100);
      strip.setPixelColor(0, strip.Color(0, 255, 0));
      strip.show();
      }
     else if(digitalRead(BUTTON_DOWN) == LOW){
      Serial.write(-1);
      delay(100);
      strip.setPixelColor(0, strip.Color(250, 0, 0));
      strip.show();
     }
  }
}
  
  
  
