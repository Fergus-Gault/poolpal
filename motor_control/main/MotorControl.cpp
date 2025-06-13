#include "MotorControl.h"
#include "CoordinateSystem.h"


void setupMotorControl() {
    int pins[] = {X_STEP_PIN, X_DIR_PIN, Y_STEP_PIN, Y_DIR_PIN, Y_DIR_PIN_2, X_ENABLE_PIN, Y_ENABLE_PIN};
    for (int pin : pins) pinMode(pin, OUTPUT);
    
    pinMode(X_CALIBRATION_BUTTON_PIN, INPUT);
    pinMode(Y_CALIBRATION_BUTTON_PIN, INPUT);
    digitalWrite(X_CALIBRATION_BUTTON_PIN, HIGH);
    digitalWrite(Y_CALIBRATION_BUTTON_PIN, HIGH);

    findOrigin(); // Find the origin by homing the motors
    disableMotors(); // Disable motors after homing
}

void enableMotors() {
    digitalWrite(X_ENABLE_PIN, LOW);
    digitalWrite(Y_ENABLE_PIN, LOW);
}

void disableMotors() {
    digitalWrite(X_ENABLE_PIN, HIGH);
    digitalWrite(Y_ENABLE_PIN, HIGH);
}

StepResult move(long xSteps, long ySteps) {
    enableMotors();

    long actualXSteps = 0;
    long actualYSteps = 0;

    if (xSteps == 0) {
        actualYSteps = moveStepper(ySteps, Y_STEP_PIN, Y_CALIBRATION_BUTTON_PIN);
        return StepResult{0, actualYSteps};
    }
    if (ySteps == 0) {
        actualXSteps = moveStepper(xSteps, X_STEP_PIN, X_CALIBRATION_BUTTON_PIN);
        return StepResult{actualXSteps, 0};
    }

    long totalSteps = max(labs(xSteps), labs(ySteps));
    float xRatio = labs(xSteps) / (float)totalSteps;
    float yRatio = labs(ySteps) / (float)totalSteps;

    long xCounter = 0;
    long yCounter = 0;

    for (long i = 0; i < totalSteps; i++) {
        if (xCounter < xRatio * (i + 1)) {
            actualXSteps += moveStepper(xSteps > 0 ? 1 : -1, X_STEP_PIN, X_CALIBRATION_BUTTON_PIN);
            xCounter++;
        }

        if (yCounter < yRatio * (i + 1)) {
            actualYSteps += moveStepper(ySteps > 0 ? 1 : -1, Y_STEP_PIN, Y_CALIBRATION_BUTTON_PIN);
            yCounter++;
        }
    }

    disableMotors();
    return StepResult{actualXSteps, actualYSteps};
}

long moveStepper(long steps, int stepPin, int limitSwitchPin) {
    long actualSteps = 0;

    if (stepPin == Y_STEP_PIN) {
        digitalWrite(Y_DIR_PIN, steps < 0 ? HIGH : LOW);
        digitalWrite(Y_DIR_PIN_2, steps > 0 ? HIGH : LOW);
    } else if (stepPin == X_STEP_PIN) {
        digitalWrite(X_DIR_PIN, steps > 0 ? HIGH : LOW);
    }

    for (long i = 0; i < labs(steps); i++) {
        if (steps < 0 && digitalRead(limitSwitchPin) == LOW) {
            if (limitSwitchPin == X_CALIBRATION_BUTTON_PIN) {
                recalibrateX();
            } else if (limitSwitchPin == Y_CALIBRATION_BUTTON_PIN) {
                recalibrateY();
            }
            return actualSteps;
        }

        digitalWrite(stepPin, HIGH);
        delayMicroseconds(MICROSTEP_DELAY);
        digitalWrite(stepPin, LOW);
        delayMicroseconds(MICROSTEP_DELAY);

        actualSteps += (steps > 0) ? 1 : -1;
    }

    return actualSteps;
}

void findOrigin() {
    enableMotors();
    recalibrateX();
    recalibrateY();
    disableMotors();
}

void recalibrateX() {
  enableMotors();
    while (digitalRead(X_CALIBRATION_BUTTON_PIN) == HIGH) {
        moveStepper(-1, X_STEP_PIN, X_CALIBRATION_BUTTON_PIN);
    }
    disableMotors();
}

void recalibrateY() {
   enableMotors();
    while (digitalRead(Y_CALIBRATION_BUTTON_PIN) == HIGH) {
        moveStepper(-1, Y_STEP_PIN, Y_CALIBRATION_BUTTON_PIN);
    }
    disableMotors();
}