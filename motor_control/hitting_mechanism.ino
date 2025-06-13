const int DIR_PIN_HIT = A5;
const int STEP_PIN_HIT = A4;
const int ENABLE_PIN_HIT = 13;
const int BUTTON_PIN_HIT = 2;
const int STEP_PIN_ROT = A2;
const int DIR_PIN_ROT = A3;
const int BUTTON_PIN_ROT = 3;

constexpr float STEP_ANGLE = 0.1125;
constexpr int STEP_DELAY_MICROS = 500;

float rotation = 0;
float targetRotation = 0;
int rotationStepsRemaining = 0;
bool hasRotationCommand = false;

float normalizeAngle(float angle) {
    while (angle >= 360) angle -= 360;
    while (angle < 0) angle += 360;
    return angle;
}

void resetRotation() {
    Serial.println("[RESET] Rotating to zero position...");
    digitalWrite(DIR_PIN_ROT, LOW);

    while (digitalRead(BUTTON_PIN_ROT) == HIGH) {
        digitalWrite(STEP_PIN_ROT, HIGH);
        delayMicroseconds(STEP_DELAY_MICROS);
        digitalWrite(STEP_PIN_ROT, LOW);
        delayMicroseconds(STEP_DELAY_MICROS);
    }

    rotation = 0;
    Serial.println("[RESET] Rotation reset complete.");
}

void setRotation(float angle) {
    if (angle < 0 || angle > 360) {
        Serial.println("[ERROR] Invalid angle. Must be between 0 and 360.");
        return;
    }

    targetRotation = normalizeAngle(angle);

    if (targetRotation == 0 && rotation != 0) {
        resetRotation();
        return;
    }

    float delta = targetRotation - rotation;
    if (delta > 180) delta -= 360;
    if (delta < -180) delta += 360;

    rotationStepsRemaining = abs(delta / STEP_ANGLE);
    hasRotationCommand = (rotationStepsRemaining > 0);
    digitalWrite(DIR_PIN_ROT, (delta > 0) ? HIGH : LOW);
}

void stepRotation() {
    if (rotationStepsRemaining > 0) {
        digitalWrite(STEP_PIN_ROT, HIGH);
        delayMicroseconds(STEP_DELAY_MICROS);
        digitalWrite(STEP_PIN_ROT, LOW);
        delayMicroseconds(STEP_DELAY_MICROS);
        rotation += (digitalRead(DIR_PIN_ROT) == HIGH) ? STEP_ANGLE : -STEP_ANGLE;
        rotation = normalizeAngle(rotation);
        rotationStepsRemaining--;
    } else {
        hasRotationCommand = false;
    }
}

void stepMotorHit(int stepDelay) {
    digitalWrite(STEP_PIN_HIT, HIGH);
    delayMicroseconds(stepDelay);
    digitalWrite(STEP_PIN_HIT, LOW);
    delayMicroseconds(stepDelay);
}

void prepareHit() {
    Serial.println("[HIT] Preparing hit mechanism...");
    digitalWrite(DIR_PIN_HIT, LOW);
    digitalWrite(ENABLE_PIN_HIT, LOW); 

    while (digitalRead(BUTTON_PIN_HIT) == HIGH) {
        stepMotorHit(2000);
    }

    delay(100);  
    Serial.println("[HIT] Hit mechanism ready.");
}

void executeHit(int strength) {
    if (strength < 0 || strength > 800) {
        Serial.println("[ERROR] Invalid strength. Must be between 0 and 800.");
        return;
    }

    Serial.println("[HIT] Executing...");
    digitalWrite(ENABLE_PIN_HIT, LOW);
    digitalWrite(DIR_PIN_HIT, HIGH);

    for (int i = 0; i < (1100 - strength); i++) {
        stepMotorHit(500);
    }
    digitalWrite(ENABLE_PIN_HIT, HIGH);

    delay(3000);  // Allow reset time
    prepareHit();
    Serial.println("[HIT] Complete. Ready for next hit.");
}

void setup() {
    pinMode(STEP_PIN_HIT, OUTPUT);
    pinMode(STEP_PIN_ROT, OUTPUT);
    pinMode(DIR_PIN_ROT, OUTPUT);
    pinMode(DIR_PIN_HIT, OUTPUT);
    pinMode(ENABLE_PIN_HIT, OUTPUT);
    pinMode(BUTTON_PIN_HIT, INPUT_PULLUP);
    pinMode(BUTTON_PIN_ROT, INPUT_PULLUP);

    Serial.begin(9600);
    digitalWrite(ENABLE_PIN_HIT, LOW); 

    Serial.println("[SYSTEM] Startup...");
    resetRotation();
    prepareHit();
}

/**
 * @brief Handles serial input commands.
 */
void handleSerialInput() {
    if (Serial.available()) {
        String input = Serial.readStringUntil('\n');
        input.trim(); // Remove spaces/newlines

        if (input.startsWith("R")) {
            String angleStr = input.substring(1);
            angleStr.trim();

            if (angleStr.length() > 0 && angleStr.toFloat() >= 0 && angleStr.toFloat() <= 360) {
                setRotation(angleStr.toFloat());
            } else {
                Serial.println("[ERROR] Invalid rotation input. Must be between 0 and 360.");
            }
        } 
        else if (input.startsWith("H")) {
            String strengthStr = input.substring(1);
            strengthStr.trim();

            if (strengthStr.length() > 0 && strengthStr.toInt() >= 0 && strengthStr.toInt() <= 800) {
                executeHit(strengthStr.toInt());
            } else {
                Serial.println("[ERROR] Invalid hit strength. Must be between 0 and 800.");
            }
        } 
        else {
            Serial.println("[ERROR] Unknown command. Use R<angle> or H<strength>.");
        }
    }
}

void loop() {
    handleSerialInput();

    if (hasRotationCommand) {
        stepRotation();
    }
}
