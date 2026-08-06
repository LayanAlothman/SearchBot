import cv2
import numpy as np
import onnxruntime as ort
import serial
import time
import os

# ============================================================
# CONFIGURATION
# ============================================================

MODEL = "best.onnx"

CLASS_NAMES = [
    "glasses",
    "key",
    "phone"
]

CONFIDENCE_THRESHOLD = 0.75
NMS_THRESHOLD = 0.45

LEFT_LIMIT = 0.35
RIGHT_LIMIT = 0.65

STOP_AREA = 15000
STOP_CONFIRMATION = 3

SAVE_FOLDER = "evidence"

os.makedirs(SAVE_FOLDER, exist_ok=True)

# ============================================================
# ARDUINO
# ============================================================

ARDUINO = False

try:

    ser = serial.Serial(
        "/dev/ttyUSB0",
        9600,
        dsrdtr=False,
        rtscts=False
    )

    ser.dtr = False
    ser.rts = False

    time.sleep(2)

    ARDUINO = True

    print("Arduino connected.")

except:

    print("Arduino not detected.")
    print("Running in Vision-Only mode.")

# ============================================================
# ONNX OPTIMIZATION
# ============================================================

session_options = ort.SessionOptions()

session_options.graph_optimization_level = (
    ort.GraphOptimizationLevel.ORT_ENABLE_ALL
)

session = ort.InferenceSession(
    MODEL,
    sess_options=session_options
)

input_name = session.get_inputs()[0].name

print("Model loaded successfully.")

# ============================================================
# CAMERA
# ============================================================

cap = cv2.VideoCapture(
    0,
    cv2.CAP_V4L2
)

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

cap.set(
    cv2.CAP_PROP_FOURCC,
    cv2.VideoWriter_fourcc(*"MJPG")
)

if not cap.isOpened():

    print("Cannot open camera.")
    exit()

print("Camera started.")

# ============================================================
# VARIABLES
# ============================================================

stop_counter = 0
lost_counter = 0
# ============================================================
# MAIN LOOP
# ============================================================

try:

    while True:

        start = time.time()

        ret, frame = cap.read()

        if not ret:
            continue

        image = frame.copy()

        h, w = image.shape[:2]

        # ----------------------------------------------------
        # PREPROCESS
        # ----------------------------------------------------

        img = cv2.resize(image, (320, 320))
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = img.astype(np.float32) / 255.0
        img = np.transpose(img, (2, 0, 1))
        img = np.expand_dims(img, 0)

        # ----------------------------------------------------
        # INFERENCE
        # ----------------------------------------------------

        output = session.run(None, {input_name: img})[0]
        output = output.squeeze().T

        boxes = []
        scores = []
        class_ids = []

        for row in output:

            x, y, bw, bh = row[:4]

            class_scores = row[4:]

            class_id = np.argmax(class_scores)

            confidence = float(class_scores[class_id])

            if confidence < CONFIDENCE_THRESHOLD:
                continue

            left = int((x - bw / 2) * w / 320)
            top = int((y - bh / 2) * h / 320)
            width = int(bw * w / 320)
            height = int(bh * h / 320)

            boxes.append([left, top, width, height])
            scores.append(confidence)
            class_ids.append(class_id)

        indices = cv2.dnn.NMSBoxes(
            boxes,
            scores,
            CONFIDENCE_THRESHOLD,
            NMS_THRESHOLD
        )

        command = "S"
        area = 0

        detected = False

        if len(indices) > 0:

            detected = True

            best = max(indices.flatten(), key=lambda i: scores[i])

            x, y, bw, bh = boxes[best]

            label = CLASS_NAMES[class_ids[best]]
            score = scores[best]

            area = bw * bh

            center_x = x + bw // 2
            relative_x = center_x / w

            # ------------------------------------------------
            # DRAW
            # ------------------------------------------------

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
                (x, y - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2
            )

            # ------------------------------------------------
            # STEERING
            # ------------------------------------------------

            if relative_x < LEFT_LIMIT:

                command = "L"

            elif relative_x > RIGHT_LIMIT:

                command = "R"

            else:

                command = "F"

            # ------------------------------------------------
            # TARGET CONFIRMATION
            # ------------------------------------------------

            centered = LEFT_LIMIT <= relative_x <= RIGHT_LIMIT

            if area >= STOP_AREA and centered:

                stop_counter += 1

                print(
                    f"Target confirmation "
                    f"{stop_counter}/{STOP_CONFIRMATION}"
                )

            else:

                stop_counter = 0

        else:

            stop_counter = 0
            lost_counter += 1

        # ----------------------------------------------------
        # DEBUG OUTPUT
        # ----------------------------------------------------

        fps = 1 / (time.time() - start)

        if detected:

            print("-" * 55)
            print(f"Object      : {label}")
            print(f"Confidence  : {score:.2f}")
            print(f"Area        : {area}")
            print(f"Direction   : {command}")
            print(f"FPS         : {fps:.1f}")
            print("-" * 55)

        else:

            print(f"Searching...    FPS = {fps:.1f}")
        # ----------------------------------------------------
        # TARGET REACHED
        # ----------------------------------------------------

        if stop_counter >= STOP_CONFIRMATION:

            filename = os.path.join(
                SAVE_FOLDER,
                "evidence.jpg"
            )

            cv2.imwrite(filename, image)

            print("\n" + "=" * 60)
            print("TARGET CONFIRMED")
            print(f"Object      : {label}")
            print(f"Confidence  : {score:.2f}")
            print(f"Area        : {area}")
            print(f"Saved Image : {filename}")
            print("=" * 60)

            # ------------------------------------------------
            # FUTURE FLASK NOTIFICATION
            # ------------------------------------------------

            # notify_target_found(label, filename)

            if ARDUINO:

                ser.write(b'T')

                for _ in range(20):
                    ser.write(b'S')
                    time.sleep(0.05)

            print("Robot stopped.")

            break

        # ----------------------------------------------------
        # SEND COMMANDS TO ARDUINO
        # ----------------------------------------------------

        if ARDUINO:

            if detected:

                lost_counter = 0

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

                if lost_counter < 4:

                    ser.write(b'S')

                else:

                    ser.write(b'A')

# ============================================================
# CLEANUP
# ============================================================

finally:

    print("\nStopping SearchBot...")

    if ARDUINO:

        for _ in range(10):

            ser.write(b'S')

            time.sleep(0.05)

        ser.close()

    cap.release()

    cv2.destroyAllWindows()

    print("Finished.")