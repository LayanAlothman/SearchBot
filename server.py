from flask import Flask, jsonify, request, send_file
import subprocess
import sys
import os
import json
import time

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

STATUS_FILE = os.path.join(
    BASE_DIR,
    "search_status.json"
)

STOP_FILE = os.path.join(
    BASE_DIR,
    "stop_requested"
)

EVIDENCE_FILE = os.path.join(
    BASE_DIR,
    "evidence",
    "evidence.jpg"
)

search_process = None
current_item = None
notification_sent = False


# ============================================================
# HELPER: WRITE STATUS
# ============================================================

def write_status(status, item=None, confidence=0, evidence=None):

    data = {
        "status": status,
        "item": item,
        "confidence": confidence
    }

    if evidence:
        data["evidence"] = evidence

    with open(STATUS_FILE, "w") as f:
        json.dump(data, f)


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():

    return jsonify({
        "status": "online",
        "message": "SearchBot App Server is running"
    })


# ============================================================
# START SEARCH
# ============================================================

@app.route("/search")
def search():

    global search_process
    global current_item
    global notification_sent

    item = request.args.get("item")

    if item not in ["glasses", "key", "phone"]:

        return jsonify({
            "status": "error",
            "message": "Invalid item",
            "valid_items": [
                "glasses",
                "key",
                "phone"
            ]
        }), 400

    # --------------------------------------------------------
    # Stop previous search if necessary
    # --------------------------------------------------------

    if search_process is not None:

        if search_process.poll() is None:

            print("Stopping previous search...")

            # Ask detector to shut down safely
            try:
                open(STOP_FILE, "w").close()
            except Exception:
                pass

            try:
                search_process.wait(timeout=5)

            except subprocess.TimeoutExpired:

                print("Detector did not stop normally.")
                print("Forcing shutdown.")

                search_process.terminate()

                try:
                    search_process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    search_process.kill()

    search_process = None

    # --------------------------------------------------------
    # Remove old stop request
    # --------------------------------------------------------

    try:
        if os.path.exists(STOP_FILE):
            os.remove(STOP_FILE)
    except Exception:
        pass

    # --------------------------------------------------------
    # Reset notification
    # --------------------------------------------------------

    notification_sent = False

    # --------------------------------------------------------
    # Reset status
    # --------------------------------------------------------

    write_status(
        "searching",
        item,
        0
    )

    print()
    print("========================================")
    print(f"New search request: {item}")
    print("========================================")

    # --------------------------------------------------------
    # Start detector
    # --------------------------------------------------------

    search_process = subprocess.Popen([
        sys.executable,
        os.path.join(BASE_DIR, "detectorAA.py"),
        item
    ])

    current_item = item

    return jsonify({
        "status": "started",
        "item": item,
        "message": f"Searching for {item}"
    })


# ============================================================
# STOP SEARCH
# ============================================================

@app.route("/stop")
def stop():

    global search_process
    global current_item
    global notification_sent

    print("Stop command received.")

    # --------------------------------------------------------
    # Ask detector to stop gracefully
    # --------------------------------------------------------

    if search_process is not None:

        if search_process.poll() is None:

            print("Requesting detector shutdown...")

            try:
                open(STOP_FILE, "w").close()
            except Exception as e:
                print(f"Could not create stop file: {e}")

            # Give detector time to send S to Arduino
            try:
                search_process.wait(timeout=5)

            except subprocess.TimeoutExpired:

                print("Detector did not stop within 5 seconds.")
                print("Forcing shutdown.")

                search_process.terminate()

                try:
                    search_process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    search_process.kill()

    # --------------------------------------------------------
    # Cleanup server state
    # --------------------------------------------------------

    search_process = None
    current_item = None
    notification_sent = False

    write_status(
        "stopped",
        None,
        0
    )

    # Remove stop request
    try:
        if os.path.exists(STOP_FILE):
            os.remove(STOP_FILE)
    except Exception:
        pass

    print("SearchBot stopped.")

    return jsonify({
        "status": "stopped",
        "message": "SearchBot stopped"
    })


# ============================================================
# STATUS
# ============================================================

@app.route("/status")
def status():

    global search_process
    global current_item

    if search_process is None:

        return jsonify({
            "status": "idle",
            "item": None
        })

    if search_process.poll() is None:

        return jsonify({
            "status": "searching",
            "item": current_item
        })

    search_process = None
    current_item = None

    return jsonify({
        "status": "idle",
        "item": None
    })


# ============================================================
# NOTIFICATION
# ============================================================

@app.route("/notification")
def notification():

    global notification_sent

    if not os.path.exists(STATUS_FILE):

        return jsonify({
            "status": "searching",
            "message": "SearchBot is searching"
        })

    try:

        with open(STATUS_FILE, "r") as f:
            data = json.load(f)

        status_value = data.get("status")
        item = data.get("item")
        confidence = data.get("confidence", 0)

        # ----------------------------------------------------
        # TARGET FOUND
        # ----------------------------------------------------

        if status_value == "found" and item:

            evidence_url = (
                "/evidence"
                if os.path.exists(EVIDENCE_FILE)
                else None
            )

            if not notification_sent:

                notification_sent = True

                message = f"{item} found"

                print()
                print("========================================")
                print("NOTIFICATION")
                print(f"Message: {message}")
                print(f"Confidence: {confidence:.2f}")
                print("========================================")

                return jsonify({
                    "status": "found",
                    "item": item,
                    "message": message,
                    "confidence": confidence,
                    "evidence": evidence_url
                })

            return jsonify({
                "status": "idle",
                "item": item,
                "message": "",
                "evidence": evidence_url
            })

        # ----------------------------------------------------
        # SEARCHING
        # ----------------------------------------------------

        if status_value == "searching":

            return jsonify({
                "status": "searching",
                "item": item,
                "message": "SearchBot is searching"
            })

        # ----------------------------------------------------
        # STOPPED / IDLE
        # ----------------------------------------------------

        return jsonify({
            "status": status_value,
            "item": item,
            "message": ""
        })

    except Exception as e:

        print(f"Notification error: {e}")

        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


# ============================================================
# EVIDENCE IMAGE
# ============================================================

@app.route("/evidence")
def evidence():

    if not os.path.exists(EVIDENCE_FILE):

        return jsonify({
            "status": "error",
            "message": "No evidence image available"
        }), 404

    return send_file(
        EVIDENCE_FILE,
        mimetype="image/jpeg"
    )


# ============================================================
# SERVER
# ============================================================

if __name__ == "__main__":

    print("========================================")
    print("SearchBot Flask Server")
    print("========================================")
    print("Server running on port 5000")
    print("========================================")

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )

