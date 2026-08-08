#ifndef MOTOR_H
#define MOTOR_H

#include <Arduino.h>

class Motor
{
public:
    void begin();
    void forward(int speed);
    void backward(int speed);
    void left(int speed);
    void right(int speed);
    void smoothLeft(int speed);  
    void smoothRight(int speed);  
    void stop();
};

#endif
