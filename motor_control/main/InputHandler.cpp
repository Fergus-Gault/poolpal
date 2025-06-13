#include "InputHandler.h"

void handleInput() {
    if (Serial.available()) {
        String input = Serial.readStringUntil('\n'); // Read input line
        input.trim(); // Remove any whitespace

        long x, y;
        if (sscanf(input.c_str(), "%ld %ld", &x, &y) == 2) { // Parse input
            if (x >= 0 && x <= MAX_X && y >= 0 && y <= MAX_Y) {
                Serial.print("Moving to: ");
                Serial.print(x);
                Serial.print(", ");
                Serial.println(y);
                moveToCoordinates(x, y); // Move to specified coordinates
            } else {
                Serial.println("Error: Coordinates out of bounds.");
                Serial.flush(); // Ensure serial buffer is clear
                return;
            }
        } else {
            Serial.println("Invalid input. Use format: X Y (e.g., 100 200)");
            Serial.flush(); // Ensure serial buffer is clear
            return;
        }
        Serial.println("Finished moving");
        Serial.flush(); // Ensure serial buffer is cleared
    }
}
