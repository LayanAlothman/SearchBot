#include "Motor.h"

// Motor Pins
const int STBY = 3;
const int PWMA = 5;
const int PWMB = 6;
const int AIN1 = 7;
const int BIN1 = 8;

void Motor::begin()
{
    pinMode(STBY, OUTPUT);
    pinMode(PWMA, OUTPUT);
    pinMode(PWMB, OUTPUT);
    pinMode(AIN1, OUTPUT);
    pinMode(BIN1, OUTPUT);

    stop();
}

void Motor::forward(int speed)
{
    digitalWrite(STBY, HIGH);
    digitalWrite(AIN1, HIGH);
    analogWrite(PWMA, speed);
    digitalWrite(BIN1, HIGH);
    analogWrite(PWMB, speed);
}

void Motor::backward(int speed)
{
    digitalWrite(STBY, HIGH);
    digitalWrite(AIN1, LOW);
    analogWrite(PWMA, speed);
    digitalWrite(BIN1, LOW);
    analogWrite(PWMB, speed);
}

void Motor::left(int speed)
{
    digitalWrite(STBY, HIGH);
    digitalWrite(AIN1, HIGH);
    analogWrite(PWMA, speed);
    digitalWrite(BIN1, LOW);
    analogWrite(PWMB, speed);
}

void Motor::right(int speed)
{
    digitalWrite(STBY, HIGH);
    digitalWrite(AIN1, LOW);
    analogWrite(PWMA, speed);
    digitalWrite(BIN1, HIGH);
    analogWrite(PWMB, speed);
}
void Motor::smoothLeft(int speed)
{
    digitalWrite(STBY, HIGH);

    // Left motor stops or goes slow, right motor moves forward
    digitalWrite(AIN1, LOW);
    analogWrite(PWMA, 0);       // Left side off

    digitalWrite(BIN1, HIGH);
    analogWrite(PWMB, speed);   // Right side moves
}

void Motor::smoothRight(int speed)
{
    digitalWrite(STBY, HIGH);

    // Left motor moves, right motor stops or goes slow
    digitalWrite(AIN1, HIGH);
    analogWrite(PWMA, speed);   // Left side moves

    digitalWrite(BIN1, LOW);
    analogWrite(PWMB, 0);       // Right side off
}
void Motor::stop()
{
    analogWrite(PWMA, 0);
    analogWrite(PWMB, 0);
    digitalWrite(AIN1, LOW);
    digitalWrite(BIN1, LOW);
    digitalWrite(STBY, HIGH);
}