from flask import Flask, Response, render_template, jsonify
from ultralytics import YOLO
from picamera2 import Picamera2
from RPLCD.i2c import CharLCD
import RPi.GPIO as GPIO
import dht11
import cv2
import time
import threading
import numpy as np

app = Flask(__name__)

# ==================================================
# Basic Settings
# ==================================================

MODEL_PATH = "best.pt"

CAMERA_WIDTH = 480
CAMERA_HEIGHT = 360

STREAM_FPS = 8
YOLO_EVERY_N_FRAMES = 8
YOLO_IMG_SIZE = 320
CONF_THRESHOLD = 0.30

# PIR Motion Sensor
PIR_PIN = 17
MOTION_HOLD_TIME = 5

# DHT11 Sensor
# DHT11 SIG -> physical pin 7 = GPIO4
DHT_PIN = 4
TEMP_HUMI_UPDATE_INTERVAL = 5

# LCD Settings
LCD_ADDRESS = 0x27   # If i2cdetect shows 0x3f, change this to 0x3f
LCD_COLS = 16
LCD_ROWS = 2

latest_result = {
    "class_name": "None",
    "confidence": 0.0,
    "message": "Waiting for motion.",
    "guide": "Temperature and humidity are displayed during idle mode.",
    "mode": "idle",
    "motion": False,
    "temperature": None,
    "humidity": None
}

lock = threading.Lock()
last_motion_time = 0

lcd = None
last_lcd_line1 = ""
last_lcd_line2 = ""

dht_sensor = None
last_env_update_time = 0
latest_temperature = None
latest_humidity = None


# ==================================================
# LCD
# ==================================================

def setup_lcd():
    global lcd

    try:
        lcd = CharLCD(
            i2c_expander="PCF8574",
            address=LCD_ADDRESS,
            port=1,
            cols=LCD_COLS,
            rows=LCD_ROWS,
            dotsize=8
        )

        lcd.clear()
        lcd_print("SYSTEM READY", "Starting...")
        print("[INFO] LCD initialized.")

    except Exception as e:
        lcd = None
        print("[WARNING] LCD initialization failed:", e)


def lcd_print(line1, line2=""):
    global last_lcd_line1, last_lcd_line2

    line1 = str(line1)[:16]
    line2 = str(line2)[:16]

    if line1 == last_lcd_line1 and line2 == last_lcd_line2:
        return

    last_lcd_line1 = line1
    last_lcd_line2 = line2

    if lcd is None:
        return

    try:
        lcd.clear()
        lcd.write_string(line1)
        lcd.cursor_pos = (1, 0)
        lcd.write_string(line2)

    except Exception as e:
        print("[WARNING] LCD print failed:", e)


def lcd_clear():
    if lcd is not None:
        try:
            lcd.clear()
        except Exception:
            pass


# ==================================================
# DHT11 Temperature / Humidity Sensor
# ==================================================

def setup_dht_sensor():
    global dht_sensor

    try:
        dht_sensor = dht11.DHT11(pin=DHT_PIN)
        print("[INFO] DHT11 sensor initialized.")
        print("[INFO] DHT11 SIG GPIO:", DHT_PIN)

    except Exception as e:
        dht_sensor = None
        print("[WARNING] DHT11 initialization failed:", e)


def read_temperature_humidity():
    global latest_temperature, latest_humidity

    if dht_sensor is None:
        return None, None

    try:
        result = dht_sensor.read()

        if result.is_valid():
            latest_temperature = float(result.temperature)
            latest_humidity = float(result.humidity)

            with lock:
                latest_result["temperature"] = latest_temperature
                latest_result["humidity"] = latest_humidity

            return latest_temperature, latest_humidity

        else:
            print("[WARNING] DHT11 read failed. Error code:", result.error_code)
            return None, None

    except Exception as e:
        print("[WARNING] DHT11 read error:", e)
        return None, None


def show_idle_environment():
    temp, humi = read_temperature_humidity()

    if temp is not None and humi is not None:
        lcd_print(f"Temp:{temp:.1f}C", f"Humi:{humi:.1f}%")

        with lock:
            latest_result["message"] = "Idle environment monitoring."
            latest_result["guide"] = f"Temp: {temp:.1f} C, Humidity: {humi:.1f} %"

    elif latest_temperature is not None and latest_humidity is not None:
        lcd_print(f"Temp:{latest_temperature:.1f}C", f"Humi:{latest_humidity:.1f}%")

        with lock:
            latest_result["message"] = "Idle environment monitoring."
            latest_result["guide"] = f"Temp: {latest_temperature:.1f} C, Humidity: {latest_humidity:.1f} %"

    else:
        lcd_print("IDLE MODE", "DHT read fail")

        with lock:
            latest_result["message"] = "Waiting for motion."
            latest_result["guide"] = "DHT11 read failed."


# ==================================================
# PIR Motion Sensor
# ==================================================

def setup_pir_sensor():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(PIR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

    print("[INFO] PIR sensor initialized.")
    print("[INFO] Waiting for PIR sensor stabilization...")
    time.sleep(10)
    print("[INFO] PIR sensor ready.")


def motion_monitor():
    global last_motion_time

    setup_pir_sensor()

    while True:
        motion_value = GPIO.input(PIR_PIN)

        if motion_value == GPIO.HIGH:
            last_motion_time = time.time()

            with lock:
                latest_result["motion"] = True
                latest_result["mode"] = "motion detected"

        else:
            if not is_motion_active():
                with lock:
                    latest_result["motion"] = False
                    latest_result["mode"] = "idle"

        time.sleep(0.2)


def is_motion_active():
    return time.time() - last_motion_time <= MOTION_HOLD_TIME


# ==================================================
# Recycling Guide
# ==================================================

def get_recycling_guide(class_name):
    name = class_name.lower().replace(" ", "_").replace("-", "_")

    guides = {
        "pet_bottle": {
            "message": "PET BOTTLE FOUND!",
            "guide": "Remove cap and label. Put it into the plastic bin.",
            "lcd1": "PET BOTTLE",
            "lcd2": "Remove label"
        },
        "bottle": {
            "message": "PET BOTTLE FOUND!",
            "guide": "Remove cap and label. Put it into the plastic bin.",
            "lcd1": "PET BOTTLE",
            "lcd2": "Remove label"
        },
        "can": {
            "message": "CAN FOUND!",
            "guide": "Empty and rinse it. Put it into the can or metal bin.",
            "lcd1": "CAN FOUND",
            "lcd2": "Rinse can"
        },
        "paper_bag": {
            "message": "PAPER WASTE FOUND!",
            "guide": "Fold it and put it into the paper recycling bin.",
            "lcd1": "PAPER FOUND",
            "lcd2": "Fold paper"
        },
        "paper": {
            "message": "PAPER WASTE FOUND!",
            "guide": "Fold it and put it into the paper recycling bin.",
            "lcd1": "PAPER FOUND",
            "lcd2": "Fold paper"
        },
        "plastic_bag": {
            "message": "PLASTIC BAG FOUND!",
            "guide": "Remove contents and put it into the plastic recycling bin.",
            "lcd1": "PLASTIC BAG",
            "lcd2": "Empty first"
        },
        "garbage_bag": {
            "message": "GENERAL WASTE FOUND!",
            "guide": "Dispose it as general waste if it cannot be recycled.",
            "lcd1": "GENERAL WASTE",
            "lcd2": "Trash bin"
        },
        "glass": {
            "message": "GLASS FOUND!",
            "guide": "Put it into the glass recycling bin carefully.",
            "lcd1": "GLASS FOUND",
            "lcd2": "Glass bin"
        }
    }

    if name in guides:
        return guides[name]

    return {
        "message": f"{class_name.upper()} FOUND!",
        "guide": "Check the recycling rule and dispose it properly.",
        "lcd1": class_name.upper()[:16],
        "lcd2": "Check rule"
    }


# ==================================================
# YOLO Model
# ==================================================

def load_yolo_model():
    print("[INFO] Loading YOLO model...")
    print("[INFO] Model path:", MODEL_PATH)

    model = YOLO(MODEL_PATH)

    print("[INFO] YOLO model loaded.")
    print("[INFO] Model classes:", model.names)

    return model


# ==================================================
# Picamera2
# ==================================================

def setup_camera():
    print("[INFO] Starting Picamera2...")

    picam2 = Picamera2()

    config = picam2.create_preview_configuration(
        main={
            "size": (CAMERA_WIDTH, CAMERA_HEIGHT),
            "format": "RGB888"
        }
    )

    picam2.configure(config)
    picam2.start()

    time.sleep(2)

    print("[INFO] Picamera2 started.")

    return picam2


def stop_camera(picam2):
    if picam2 is not None:
        try:
            print("[INFO] Stopping Picamera2...")
            picam2.stop()
            picam2.close()
            print("[INFO] Picamera2 stopped.")
        except Exception as e:
            print("[WARNING] Camera stop error:", e)


# ==================================================
# YOLO Detection
# ==================================================

def run_yolo_detection(model, frame):
    results = model.predict(
        source=frame,
        conf=CONF_THRESHOLD,
        imgsz=YOLO_IMG_SIZE,
        device="cpu",
        verbose=False
    )

    result = results[0]
    annotated_frame = result.plot()

    if result.boxes is not None and len(result.boxes) > 0:
        best_box = max(result.boxes, key=lambda box: float(box.conf[0]))

        class_id = int(best_box.cls[0])
        detected_name = result.names[class_id]
        detected_conf = float(best_box.conf[0])

        guide_data = get_recycling_guide(detected_name)

        lcd_print(guide_data["lcd1"], guide_data["lcd2"])

        with lock:
            latest_result["class_name"] = detected_name
            latest_result["confidence"] = round(detected_conf, 2)
            latest_result["message"] = guide_data["message"]
            latest_result["guide"] = guide_data["guide"]
            latest_result["mode"] = "YOLO detection"
            latest_result["motion"] = True

    else:
        lcd_print("NO WASTE", "Try again")

        with lock:
            latest_result["class_name"] = "None"
            latest_result["confidence"] = 0.0
            latest_result["message"] = "No waste detected."
            latest_result["guide"] = "Please place waste in front of the camera."
            latest_result["mode"] = "YOLO detection"
            latest_result["motion"] = True

    return annotated_frame


# ==================================================
# Idle Frame
# ==================================================

def create_idle_frame():
    frame = np.zeros((CAMERA_HEIGHT, CAMERA_WIDTH, 3), dtype=np.uint8)

    cv2.putText(
        frame,
        "IDLE MODE",
        (140, 140),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.1,
        (255, 255, 255),
        2
    )

    cv2.putText(
        frame,
        "Temp/Humi on LCD",
        (95, 190),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (255, 255, 255),
        2
    )

    cv2.putText(
        frame,
        "Camera + YOLO OFF",
        (95, 240),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2
    )

    return frame


# ==================================================
# Video Streaming
# ==================================================

def generate_frames():
    global last_env_update_time

    model = load_yolo_model()

    picam2 = None
    frame_count = 0
    last_annotated_frame = None
    frame_delay = 1.0 / STREAM_FPS

    while True:
        start_time = time.time()

        if not is_motion_active():
            if picam2 is not None:
                stop_camera(picam2)
                picam2 = None
                last_annotated_frame = None

            if time.time() - last_env_update_time >= TEMP_HUMI_UPDATE_INTERVAL:
                show_idle_environment()
                last_env_update_time = time.time()

            with lock:
                latest_result["class_name"] = "None"
                latest_result["confidence"] = 0.0
                latest_result["mode"] = "idle"
                latest_result["motion"] = False

            output_frame = create_idle_frame()

        else:
            if picam2 is None:
                lcd_print("CAMERA ON", "Detecting...")
                picam2 = setup_camera()
                frame_count = 0
                last_annotated_frame = None

            try:
                frame = picam2.capture_array()

            except Exception as e:
                print("[ERROR] Failed to capture Picamera2 frame:", e)
                lcd_print("CAMERA ERROR", "Check camera")
                output_frame = create_idle_frame()
                time.sleep(0.1)
                continue

            frame_count += 1

            if frame_count % YOLO_EVERY_N_FRAMES == 0:
                try:
                    last_annotated_frame = run_yolo_detection(model, frame)

                except Exception as e:
                    print("[ERROR] YOLO detection failed:", e)
                    lcd_print("YOLO ERROR", "Check model")
                    last_annotated_frame = frame

                    with lock:
                        latest_result["class_name"] = "None"
                        latest_result["confidence"] = 0.0
                        latest_result["message"] = "YOLO detection error."
                        latest_result["guide"] = str(e)
                        latest_result["mode"] = "YOLO error"
                        latest_result["motion"] = True

            if last_annotated_frame is not None:
                output_frame = last_annotated_frame
            else:
                output_frame = frame

        ret, buffer = cv2.imencode(
            ".jpg",
            output_frame,
            [cv2.IMWRITE_JPEG_QUALITY, 70]
        )

        if not ret:
            print("[WARNING] JPEG encode failed.")
            continue

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"
        )

        elapsed = time.time() - start_time
        sleep_time = frame_delay - elapsed

        if sleep_time > 0:
            time.sleep(sleep_time)


# ==================================================
# Flask Routes
# ==================================================

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/video_feed")
def video_feed():
    return Response(
        generate_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )


@app.route("/result")
def result():
    with lock:
        data = latest_result.copy()

    return jsonify(data)


# ==================================================
# Main
# ==================================================

if __name__ == "__main__":
    print("===================================")
    print("AIoT Smart Recycling Flask Server")
    print("Motion + Camera + YOLO + LCD + DHT11 Mode")
    print("MODEL:", MODEL_PATH)
    print("PIR GPIO:", PIR_PIN)
    print("DHT11 GPIO:", DHT_PIN)
    print("LCD ADDRESS:", hex(LCD_ADDRESS))
    print("CAMERA SIZE:", CAMERA_WIDTH, "x", CAMERA_HEIGHT)
    print("STREAM FPS:", STREAM_FPS)
    print("YOLO every", YOLO_EVERY_N_FRAMES, "frames")
    print("Open: http://<RaspberryPi-IP>:5000")
    print("===================================")

    GPIO.setwarnings(False)
    GPIO.cleanup()
    GPIO.setmode(GPIO.BCM)

    setup_lcd()
    setup_dht_sensor()

    pir_thread = threading.Thread(target=motion_monitor, daemon=True)
    pir_thread.start()

    try:
        app.run(
            host="0.0.0.0",
            port=5000,
            debug=False,
            threaded=True
        )

    finally:
        lcd_clear()
        GPIO.cleanup()
