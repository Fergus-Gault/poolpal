#ifndef MOTORCONTROL_H
#define MOTORCONTROL_H

#include <Arduino.h>

// Constants and pin definitions
constexpr int MICROSTEP_DELAY = 50; // Delay between steps in microseconds

// Motor driver pin definitions
constexpr int X_ENABLE_PIN = A0;
constexpr int X_STEP_PIN   = A4;
constexpr int X_DIR_PIN    = A3;

constexpr int Y_ENABLE_PIN = 7;
constexpr int Y_STEP_PIN   = 3;
constexpr int Y_DIR_PIN    = 2;
constexpr int Y_DIR_PIN_2  = 8;

// Calibration button pins
constexpr int X_CALIBRATION_BUTTON_PIN = 9;
constexpr int Y_CALIBRATION_BUTTON_PIN = 10;

// Custom struct to hold the X and Y steps
struct StepResult {
    long xSteps;
    long ySteps;
};

// Function declarations
void setupMotorControl();
void enableMotors();
void disableMotors();
StepResult move(long xSteps, long ySteps);
long moveStepper(long steps, int stepPin, int calibrationButtonPin);
void findOrigin();
void recalibrateX(); // New function for recalibrating X
void recalibrateY(); // New function for recalibrating Y

#endif
