import cv2
import numpy as np
import onnxruntime as ort
import serial
import time
import os

# -----------------------------
# SETTINGS
# -----------------------------

MODEL = "best.onnx"

CLASS_NAMES = [
    "glasses",
    "key",
    "phone"
]

CONFIDENCE_THRESHOLD = 0.60
NMS_THRESHOLD = 0.45

LEFT_LIMIT = 0.35
RIGHT_LIMIT = 0.65

STOP_AREA = 15000

# -----------------------------
# TARGET SELECTION
# -----------------------------

print()
print("=" * 45)
print("          SearchBot Target Selection")
print("=" * 45)
print()

for i, name in enumerate(CLASS_NAMES, start=1):
    print(f"{i}. {name}")

print()

while True:

    choice = input("Choose an object to search for: ").strip()

    if choice in ["1", "2", "3"]:
        target_class_id = int(choice) - 1
        target_object = CLASS_NAMES[target_class_id]
        break

    print("Invalid choice. Please enter 1, 2, or 3.")

print()
print(f"Target selected: {target_object}")
print()

# -----------------------------
# SERIAL
# -----------------------------

ser = serial.Serial(
    "/dev/ttyUSB0",
    9600,
    dsrdtr=False,
    rtscts=False
)

ser.dtr = False
ser.rts = False

time.sleep(2)

# -----------------------------
# YOLO
# -----------------------------

session = ort.InferenceSession(MODEL)
input_name = session.get_inputs()[0].name

print("Model loaded.")

# -----------------------------
# CAMERA
# -----------------------------

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Cannot open camera")
    ser.close()
    exit()

print("Camera started.")
print(f"Searching for: {target_object}")
print()

# -----------------------------
# EVIDENCE FOLDER
# -----------------------------

os.makedirs("evidence", exist_ok=True)

# -----------------------------
# MAIN LOOP
# -----------------------------

try:

    while True:

        start = time.time()

        ret, frame = cap.read()

        if not ret:
            continue

        image = frame.copy()

        h, w = image.shape[:2]

        # -----------------------------
        # PREPROCESS
        # -----------------------------

        img = cv2.resize(image, (320, 320))

        img = cv2.cvtColor(
            img,
            cv2.COLOR_BGR2RGB
        )

        img = img.astype(np.float32) / 255.0

        img = np.transpose(
            img,
            (2, 0, 1)
        )

        img = np.expand_dims(
            img,
            0
        )

        # -----------------------------
        # INFERENCE
        # -----------------------------

        output = session.run(
            None,
            {input_name: img}
        )[0]

        output = output.squeeze().T

        boxes = []
        scores = []
        class_ids = []

        # -----------------------------
        # PROCESS DETECTIONS
        # -----------------------------

        for row in output:

            x, y, bw, bh = row[:4]

            class_scores = row[4:]

            class_id = np.argmax(class_scores)

            confidence = float(
                class_scores[class_id]
            )

            if confidence < CONFIDENCE_THRESHOLD:
                continue

            # IMPORTANT:
            # Ignore every object except
            # the object selected at startup.

            if class_id != target_class_id:
                continue

            left = int(
                (x - bw / 2) * w / 320
            )

            top = int(
                (y - bh / 2) * h / 320
            )

            width = int(
                bw * w / 320
            )

            height = int(
                bh * h / 320
            )

            boxes.append(
                [left, top, width, height]
            )

            scores.append(confidence)

            class_ids.append(class_id)

        # -----------------------------
        # NMS
        # -----------------------------

        indices = cv2.dnn.NMSBoxes(
            boxes,
            scores,
            CONFIDENCE_THRESHOLD,
            NMS_THRESHOLD
        )

        command = "S"
        area = 0
        label = None
        score = 0

        # -----------------------------
        # BEST TARGET
        # -----------------------------

        if len(indices) > 0:

            best = max(
                indices.flatten(),
                key=lambda i: scores[i]
            )

            x, y, bw, bh = boxes[best]

            label = CLASS_NAMES[
                class_ids[best]
            ]

            score = scores[best]

            area = bw * bh

            center_x = x + bw // 2

            # -----------------------------
            # DIRECTION
            # -----------------------------

            relative_x = center_x / w

            if relative_x < LEFT_LIMIT:

                command = "L"

            elif relative_x > RIGHT_LIMIT:

                command = "R"

            else:

                command = "F"

            # -----------------------------
            # DRAW DETECTION
            # -----------------------------

            cv2.rectangle(
                image,
                (x, y),
                (x + bw, y + bh),
                (0, 255, 0),
                2
            )

            cv2.putText(
                image,
                f"{label} {score:.2f}",
                (x, max(y - 10, 20)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2
            )

        # -----------------------------
        # TARGET FOUND
        # -----------------------------

        if area >= STOP_AREA:

            print()
            print("=" * 55)
            print("             TARGET CONFIRMED")
            print("=" * 55)

            print(f"Object      : {label}")
            print(f"Confidence  : {score:.2f}")
            print(f"Area        : {area}")
            print(f"Direction   : {command}")

            # -----------------------------
            # SAVE EVIDENCE
            # -----------------------------

            filename = "evidence/evidence.jpg"

            saved = cv2.imwrite(
                filename,
                image
            )

            if saved:

                print(
                    f"Saved Image : {filename}"
                )

            else:

                print(
                    "ERROR: Could not save image!"
                )

            print("=" * 55)

            # -----------------------------
            # STOP ROBOT
            # -----------------------------

            ser.write(b'T')

            for _ in range(20):

                ser.write(b'S')

                time.sleep(0.05)

            print("Robot stopped.")

            break

        # -----------------------------
        # PRINT STATUS
        # -----------------------------

        print(
            f"Target = {target_object:<8} "
            f"Area = {area:<8} "
            f"Command = {command}"
        )

        # -----------------------------
        # SEND COMMANDS
        # -----------------------------

        if len(indices) > 0:

            # Tracking mode
            ser.write(b'T')

            if command == "F":

                ser.write(b'F')

            elif command == "L":

                ser.write(b'L')

            elif command == "R":

                ser.write(b'R')

            else:

                ser.write(b'S')

        else:

            # No target detected
            # Autonomous search
            ser.write(b'A')

        # -----------------------------
        # FPS
        # -----------------------------

        fps = 1 / (time.time() - start)

        print(
            f"FPS: {fps:.1f}"
        )

except KeyboardInterrupt:

    print()
    print("Search interrupted by user.")

finally:

    print()
    print("Stopping SearchBot...")

    # Multiple STOP commands
    # for safety.

    for _ in range(10):

        ser.write(b'S')

        time.sleep(0.05)

    cap.release()

    ser.close()

    print("Finished.")