import cv2
import numpy as np
import onnxruntime as ort
import serial
import time
import sys
import os
import json


# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

MODEL = os.path.join(
    BASE_DIR,
    "best.onnx"
)

STATUS_FILE = os.path.join(
    BASE_DIR,
    "search_status.json"
)

EVIDENCE_DIR = os.path.join(
    BASE_DIR,
    "evidence"
)

EVIDENCE_FILE = os.path.join(
    EVIDENCE_DIR,
    "evidence.jpg"
)


# ============================================================
# SETTINGS
# ============================================================

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


# ============================================================
# TARGET SELECTION
# ============================================================

if len(sys.argv) < 2:

    print("Usage:")
    print("  python detectorAA.py glasses")
    print("  python detectorAA.py key")
    print("  python detectorAA.py phone")

    sys.exit(1)


TARGET = sys.argv[1].lower()


if TARGET not in CLASS_NAMES:

    print(f"Invalid target: {TARGET}")
    print("Valid targets: glasses, key, phone")

    sys.exit(1)


print("========================================")
print("SearchBot Object Detection")
print("========================================")
print(f"Target: {TARGET}")
print("========================================")


# ============================================================
# RESET SEARCH STATUS
# ============================================================

with open(STATUS_FILE, "w") as f:

    json.dump(
        {
            "status": "searching",
            "item": TARGET,
            "confidence": 0
        },
        f
    )


# ============================================================
# EVIDENCE FOLDER
# ============================================================

EVIDENCE_FILE = os.path.join(
    EVIDENCE_DIR,
    "evidence.jpg"
)
STOP_FILE = os.path.join(
    BASE_DIR,
    "stop_requested"
)

# ============================================================
# SERIAL
# ============================================================

try:

    ser = serial.Serial(
        "/dev/ttyUSB0",
        9600,
        dsrdtr=False,
        rtscts=False
    )

except Exception as e:

    print("Could not open Arduino serial port.")
    print(e)

    with open(STATUS_FILE, "w") as f:

        json.dump(
            {
                "status": "error",
                "item": TARGET,
                "confidence": 0,
                "message": "Could not connect to Arduino"
            },
            f
        )

    sys.exit(1)


ser.dtr = False
ser.rts = False

time.sleep(2)

print("Arduino connected.")


# ============================================================
# YOLO / ONNX
# ============================================================

try:

    session = ort.InferenceSession(
        MODEL
    )

    input_name = session.get_inputs()[0].name

except Exception as e:

    print("Could not load ONNX model.")
    print(e)

    ser.close()

    with open(STATUS_FILE, "w") as f:

        json.dump(
            {
                "status": "error",
                "item": TARGET,
                "confidence": 0,
                "message": "Could not load ONNX model"
            },
            f
        )

    sys.exit(1)


print("YOLO model loaded.")


# ============================================================
# CAMERA
# ============================================================

cap = cv2.VideoCapture(0)

cap.set(
    cv2.CAP_PROP_FRAME_WIDTH,
    640
)

cap.set(
    cv2.CAP_PROP_FRAME_HEIGHT,
    480
)


if not cap.isOpened():

    print("Cannot open camera.")

    ser.close()

    with open(STATUS_FILE, "w") as f:

        json.dump(
            {
                "status": "error",
                "item": TARGET,
                "confidence": 0,
                "message": "Cannot open camera"
            },
            f
        )

    sys.exit(1)


print("Camera started.")


# ============================================================
# MAIN SEARCH LOOP
# ============================================================

try:

    while True:
        if os.path.exists(STOP_FILE):
            print("Stop request received from Flask.")  
            try:
                for _ in range(10):
                   ser.write(b"S")
                   time.sleep(0.05)
                print("Arduino STOP command sent.")
            except Exception as e:
                print(f"Could not send STOP command: {e}")
            break
            
        start = time.time()


        # ====================================================
        # READ CAMERA
        # ====================================================

        ret, frame = cap.read()


        if not ret:

            print("Camera frame failed.")

            continue


        image = frame.copy()

        h, w = image.shape[:2]


        # ====================================================
        # PREPROCESS
        # ====================================================

        img = cv2.resize(
            image,
            (320, 320)
        )

        img = cv2.cvtColor(
            img,
            cv2.COLOR_BGR2RGB
        )

        img = img.astype(
            np.float32
        ) / 255.0

        img = np.transpose(
            img,
            (2, 0, 1)
        )

        img = np.expand_dims(
            img,
            0
        )


        # ====================================================
        # INFERENCE
        # ====================================================

        output = session.run(
            None,
            {
                input_name: img
            }
        )[0]

        output = output.squeeze().T


        # ====================================================
        # DETECTION ARRAYS
        # ====================================================

        boxes = []
        scores = []
        class_ids = []


        # ====================================================
        # PROCESS YOLO RESULTS
        # ====================================================

        for row in output:

            x, y, bw, bh = row[:4]

            class_scores = row[4:]


            class_id = int(
                np.argmax(class_scores)
            )

            confidence = float(
                class_scores[class_id]
            )


            if confidence < CONFIDENCE_THRESHOLD:

                continue


            left = int(
                (x - bw / 2)
                * w
                / 320
            )

            top = int(
                (y - bh / 2)
                * h
                / 320
            )

            width = int(
                bw
                * w
                / 320
            )

            height = int(
                bh
                * h
                / 320
            )


            boxes.append(
                [
                    left,
                    top,
                    width,
                    height
                ]
            )

            scores.append(
                confidence
            )

            class_ids.append(
                class_id
            )


        # ====================================================
        # NMS
        # ====================================================

        if len(boxes) > 0:

            indices = cv2.dnn.NMSBoxes(
                boxes,
                scores,
                CONFIDENCE_THRESHOLD,
                NMS_THRESHOLD
            )

        else:

            indices = []


        # ====================================================
        # DEFAULT STATE
        # ====================================================

        target_found = False

        label = ""

        score = 0.0

        area = 0

        center_x = 0


        # ====================================================
        # SELECT TARGET
        # ====================================================

        if len(indices) > 0:

            target_indices = []


            for i in np.array(
                indices
            ).flatten():

                detected_class = CLASS_NAMES[
                    class_ids[i]
                ]


                if detected_class == TARGET:

                    target_indices.append(
                        i
                    )


            if len(target_indices) > 0:

                best = max(
                    target_indices,
                    key=lambda i: scores[i]
                )


                x, y, bw, bh = boxes[best]


                label = CLASS_NAMES[
                    class_ids[best]
                ]

                score = scores[best]

                area = bw * bh

                center_x = x + bw // 2

                target_found = True


                # =================================================
                # DRAW TARGET
                # =================================================

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
                    (
                        x,
                        max(y - 10, 25)
                    ),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 0),
                    2
                )


        # ====================================================
        # TARGET CONFIRMED
        # ====================================================

        if target_found and area >= STOP_AREA:

            # ------------------------------------------------
            # SAVE IMAGE
            # ------------------------------------------------

            success = cv2.imwrite(
                EVIDENCE_FILE,
                image
            )


            print()
            print(
                "============================================================"
            )

            print(
                "TARGET CONFIRMED"
            )

            print(
                f"Object      : {label}"
            )

            print(
                f"Confidence  : {score:.2f}"
            )

            print(
                f"Area        : {area}"
            )

            print(
                f"Saved Image : {EVIDENCE_FILE}"
            )

            print(
                "============================================================"
            )


            # ------------------------------------------------
            # UPDATE STATUS FOR FLASK
            # ------------------------------------------------

            with open(
                STATUS_FILE,
                "w"
            ) as f:

                json.dump(
                    {
                        "status": "found",
                        "item": label,
                        "confidence": score,
                        "evidence": "evidence/evidence.jpg"
                    },
                    f
                )


            print(
                "Notification status updated."
            )


            # ------------------------------------------------
            # TELL ARDUINO TARGET WAS FOUND
            # ------------------------------------------------

            print(
                "Sending T command to Arduino..."
            )

            ser.write(
                b"T"
            )


            # Allow Arduino to process T
            time.sleep(
                1.0
            )


            # ------------------------------------------------
            # SAFETY STOP
            # ------------------------------------------------

            for _ in range(10):

                ser.write(
                    b"S"
                )

                time.sleep(
                    0.05
                )


            print(
                "Robot stopped."
            )


            break


        # ====================================================
        # NORMAL STATUS
        # ====================================================

        print(
            f"Target = {TARGET}   "
            f"Found = {target_found}   "
            f"Area = {area}"
        )


        # ====================================================
        # ROBOT CONTROL
        #
        # THIS IS YOUR ORIGINAL WORKING BEHAVIOR.
        # ====================================================

        if target_found:

            # Target visible

            ser.write(
                b"T"
            )

            ser.write(
                b"S"
            )

        else:

            # Target not visible
            # Arduino performs autonomous search

            ser.write(
                b"A"
            )


        # ====================================================
        # FPS
        # ====================================================

        elapsed = time.time() - start


        if elapsed > 0:

            fps = 1.0 / elapsed

        else:

            fps = 0


        print(
            f"FPS: {fps:.1f}"
        )


    print(
        "Stopping SearchBot..."
    )


# ============================================================
# CLEANUP
# ============================================================

finally:

    print(
        "Performing safety shutdown..."
    )


    # --------------------------------------------------------
    # STOP ARDUINO
    # --------------------------------------------------------

    try:

        for _ in range(10):

            ser.write(
                b"S"
            )

            time.sleep(
                0.05
            )

    except Exception:

        pass


    # --------------------------------------------------------
    # CAMERA
    # --------------------------------------------------------

    try:

        cap.release()

    except Exception:

        pass


    # --------------------------------------------------------
    # SERIAL
    # --------------------------------------------------------

    try:

        ser.close()

    except Exception:

        pass


    print(
        "Finished."
    )