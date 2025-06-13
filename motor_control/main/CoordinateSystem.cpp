#include "CoordinateSystem.h"
#include "MotorControl.h"

// Internal variables to store current position
static long currentX = 0;
static long currentY = 0;

void setupCoordinates() {
    resetCoordinates();
    pinMode(TRIG_PIN, OUTPUT);
    pinMode(ECHO_PIN, INPUT);
}

void updateCoordinates(long x, long y) {
    currentX += x;
    currentY += y;
}

void resetCoordinates() {
    currentX = 0;
    currentY = 0;
}

long getCurrentX() {
    return currentX;
}

long getCurrentY() {
    return currentY;
}

void moveToCoordinates(long x, long y) {
    if (x == 0) {
        recalibrateX();
        currentX = 0;
    }
    if (y == 0) {
        recalibrateY();
        currentY = 0;
    }

    enableMotors();  // Make sure motors are enabled

    long xSteps = x - currentX;
    long ySteps = y - currentY;

    StepResult actualSteps = move(xSteps, ySteps);
    updateCoordinates(actualSteps.xSteps, actualSteps.ySteps);
    disableMotors();
}


float getDistance() {
    float duration;
    float distance;
    digitalWrite(TRIG_PIN, LOW);
    delayMicroseconds(2);
    digitalWrite(TRIG_PIN, HIGH);
    delayMicroseconds(10);
    digitalWrite(TRIG_PIN, LOW);
    duration = pulseIn(ECHO_PIN, HIGH);
    distance = (duration * 0.0343) / 2;
    delay(100);
    return distance;
}
