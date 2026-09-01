# SearchBot
SearchBot is an autonomous mobile robot designed to search an indoor environment for predefined everyday objects using artificial intelligence and computer vision.

# Overview

The system uses a custom-trained object detection model to identify three target objects: phones, keys, and glasses. The model runs locally on a Raspberry Pi, which communicates with an Arduino responsible for controlling the robot's motors, ultrasonic sensor, and buzzer.

A Flask server connects the robotic system to a MIT App Inventor mobile application, allowing the user to select a target, control the robot, monitor its status, and receive a notification when the target is found.

# Features

- AI-based object detection
- Autonomous indoor searching
- Local inference on Raspberry Pi
- Raspberry Pi–Arduino serial communication
- Ultrasonic obstacle safety
- Target confirmation buzzer
- Mobile application for remote control
- Evidence image captured when the target is found

# AI Model

A custom object detection model was trained to recognize three target classes: phones, keys, and glasses. The model was evaluated using precision, recall, mAP@50, and mAP@50–95.

The trained model was exported to ONNX format and deployed on a Raspberry Pi using ONNX Runtime for local inference.

# Deployment

The trained model was deployed on a Raspberry Pi 4 using ONNX Runtime for local inference. The system achieved an average inference latency of 122.58 ms, corresponding to 8.16 FPS, with approximately 86 MB of RAM usage.

## Hardware & Communication

The robotic system combines a Raspberry Pi 4 and Arduino for processing and hardware control. The Arduino controls the motors, ultrasonic sensor, and buzzer, while serial communication enables the Raspberry Pi and Arduino to exchange commands and status information.

# Results

## Model Performance

| Metric | Result |
|---|---:|
| Precision | 86.09% |
| Recall | 71.49% |
| mAP@50 | 76.15% |
| mAP@50–95 | 55.89% |

## Real-World Search Trials

The complete system was evaluated through 30 real-world search trials.

| Target | Success Rate |
|---|---:|
| Phone | 100% |
| Key | 80% |
| Glasses | 80% |
| Overall | 86.67% |
