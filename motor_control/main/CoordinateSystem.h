#ifndef COORDINATESYSTEM_H
#define COORDINATESYSTEM_H

#include <Arduino.h>
#include "MotorControl.h" 

// Define movement boundaries
constexpr long MAX_X = 36000;
constexpr long MAX_Y = 72000;

constexpr int TRIG_PIN = 11;
constexpr int ECHO_PIN = 12;

void setupCoordinates();
void updateCoordinates(long x, long y);
void resetCoordinates();
long getCurrentX();
long getCurrentY();
float getDistance();
void moveToCoordinates(long x, long y);

#endif
