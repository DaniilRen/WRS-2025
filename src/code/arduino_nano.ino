//код для ардуино нано 
#include <Servo.h>
#include <SoftwareSerial.h>

int dir;

Servo motor;

void setup() {
  Serial.begin(9600);
  motor.attach(3);
  motor.writeMicroseconds(1500);
  delay(5000);
}

void loop() {
  if (Serial.available()>0){
    dir = Serial.read();
    Serial.print("Success");
  }
  if (dir == 0){
    motor.writeMicroseconds(1500);
  }
  else if (dir == 1){
    motor.writeMicroseconds(1900);
  }
 else if (dir == -1){
  motor.writeMicroseconds(1000);
 }
  }
  
