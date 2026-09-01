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
