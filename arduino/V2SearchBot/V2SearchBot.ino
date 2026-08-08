#include "Motor.h"
#include "Ultrasonic.h"

Motor motor;
Ultrasonic ultrasonic;

// -----------------------------
// SETTINGS
// -----------------------------

const int SEARCH_SPEED = 65;
const int TRACK_SPEED  = 65;
const int TURN_SPEED   = 65;

// Safety distance set to 20cm to protect the camera lens
const int SAFE_DISTANCE = 20;


// -----------------------------

bool trackingMode = false;
bool searchMode = false;

char command = 'S';

// -----------------------------

void setup()
{
    Serial.begin(9600);

    motor.begin();
    ultrasonic.begin();

   
    motor.stop();

    Serial.println("SearchBot Ready");
}

// -----------------------------

void loop()
{
    // 1. Always check the distance first
    int dist = ultrasonic.distance();

    // 2. Read Raspberry Pi command
    while (Serial.available() > 0)
    {
        char latest = Serial.read();

if (latest == 'A')
{
    searchMode = true;
    trackingMode = false;

    Serial.println("SEARCH MODE");
}

else if (latest == 'X')
{
    searchMode = false;
    trackingMode = false;

    motor.stop();

    Serial.println("IDLE MODE");
}

else if (latest == 'F' ||
         latest == 'L' ||
         latest == 'R' ||
         latest == 'S' ||
         latest == 'T')
{
    searchMode = false;
    trackingMode = true;

    command = latest;
}
    }

    // =====================================================
    // TRACK MODE
    // =====================================================
    if (trackingMode)
    {
        // EMERGENCY BRAKE: Overrides movement if the camera gets too close to a wall
        if (dist > 0 && dist <= SAFE_DISTANCE) {
            if (command == 'F' || command == 'L' || command == 'R') {
                command = 'S'; // Force stop
                Serial.println("EMERGENCY STOP - PROTECTING CAMERA!");
            }
        }

        switch(command)
        {
            case 'F':
                motor.forward(TRACK_SPEED);
                break;

            case 'L':
                motor.smoothLeft(TURN_SPEED);
                break;

            case 'R':
                motor.smoothRight(TURN_SPEED);
                break;

            case 'T':
                motor.stop();
                delay(100);
                
                command = 'S'; // Reset to 'S' so it doesn't beep forever
                break;

            case 'S':
            default:
                motor.stop();
                break;
        }

        return; // Skip search mode entirely while tracking
    }
if (!searchMode)
{
    motor.stop();
    return;
}
    // =====================================================
    // SEARCH MODE
    // =====================================================
    
    // Print distance to serial monitor for debugging
    Serial.print("Search Distance: ");
    Serial.println(dist);

    if (dist > SAFE_DISTANCE || dist == 0) // (dist == 0 usually means nothing is in range for the HC-SR04)
    {
        motor.forward(SEARCH_SPEED);
        delay(250);
    }
    else
    {
        motor.stop();
        delay(300);

        motor.right(TURN_SPEED);
        delay(500);

        motor.stop();
        delay(150);
    }
}