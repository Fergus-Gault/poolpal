#include "MotorControl.h"
#include "CoordinateSystem.h"
#include "InputHandler.h" 

void setup() {
    Serial.begin(115200); 
    setupMotorControl();
    setupCoordinates();
}

void loop() {
    //Serial.println(getDistance());
    //Serial.println(digitalRead(Y_CALIBRATION_BUTTON_PIN));
    handleInput();
}
