# IoT26-TermProject
# AIoT Smart Recycling System

## 1. Project Overview

This project is an AIoT-based smart recycling assistant using Raspberry Pi, YOLO, sensors, camera, Flask, and LCD display.

The system detects user motion, activates the camera, classifies waste using a YOLO model, and provides simple recycling guidance through a 16x2 LCD.

During idle mode, the system displays temperature and humidity using the DHT11 sensor.

---

## 2. Project Goal

The goal of this project is to reduce recycling mistakes by providing immediate waste classification and disposal guidance.

The system was designed as a working prototype that combines AI vision, IoT sensors, and real-time user feedback.

---

## 3. Main Features

* PIR motion-based system activation
* Camera activation only when motion is detected
* YOLO-based waste detection
* LCD output for waste type and recycling guidance
* DHT11 temperature and humidity display during idle mode
* Flask-based local web monitoring page
* Raspberry Pi-based AIoT system integration

---

## 4. System Architecture

| Part               | Component      | Role                                         |
| ------------------ | -------------- | -------------------------------------------- |
| Main Board         | Raspberry Pi   | Runs Python, Flask, YOLO, and sensor control |
| Camera             | Pi Camera      | Captures waste images                        |
| AI Model           | YOLO `best.pt` | Detects and classifies waste                 |
| Motion Sensor      | PIR Sensor     | Detects user motion                          |
| Environment Sensor | DHT11          | Measures temperature and humidity            |
| Display            | 16x2 I2C LCD   | Shows result and recycling guide             |
| Web Server         | Flask          | Provides local camera streaming page         |

---

## 5. Hardware Configuration

### PIR Sensor

| PIR Pin | Raspberry Pi Pin |
| ------- | ---------------- |
| VCC     | 5V               |
| GND     | GND              |
| OUT     | GPIO17           |

### DHT11 Sensor

| DHT11 Pin | Raspberry Pi Pin      |
| --------- | --------------------- |
| VCC       | 3.3V, Physical Pin 1  |
| GND       | GND, Physical Pin 9   |
| SIG       | GPIO4, Physical Pin 7 |

### I2C LCD

| LCD Pin | Raspberry Pi Pin      |
| ------- | --------------------- |
| VCC     | 5V                    |
| GND     | GND                   |
| SDA     | GPIO2, Physical Pin 3 |
| SCL     | GPIO3, Physical Pin 5 |

### Camera

| Camera    | Raspberry Pi |
| --------- | ------------ |
| Pi Camera | Camera Port  |

---

## 6. Software Stack

| Software / Library | Purpose                               |
| ------------------ | ------------------------------------- |
| Python             | Main programming language             |
| Flask              | Web server and live camera page       |
| YOLO / Ultralytics | Waste object detection                |
| Picamera2          | Raspberry Pi camera control           |
| RPi.GPIO           | GPIO sensor control                   |
| RPLCD              | LCD control                           |
| dht11              | DHT11 temperature and humidity sensor |
| OpenCV             | Image processing                      |
| Google Colab       | YOLO model training                   |
| Roboflow           | Waste detection dataset               |

---

## 7. AI Model

The AI model was prepared using a waste detection dataset from Roboflow Universe.

The model was fine-tuned in Google Colab, and the trained `best.pt` file was applied to the Raspberry Pi.

### Target Waste Classes

* PET Bottle
* Can
* Paper
* Plastic Bag
* Garbage Bag
* Glass

---

## 8. Operation Flow

1. The system starts in idle mode.
2. DHT11 measures temperature and humidity.
3. LCD displays temperature and humidity.
4. PIR sensor detects user motion.
5. Camera is activated.
6. YOLO model analyzes the camera image.
7. The system detects the waste type.
8. LCD displays the waste type and recycling instruction.
9. If no motion is detected, the system returns to idle mode.

---

## 9. LCD Output Logic

| System State           | LCD Output                |
| ---------------------- | ------------------------- |
| Idle Mode              | Temperature and humidity  |
| Motion Detected        | CAMERA ON / Detecting     |
| PET Bottle Detected    | PET BOTTLE / Remove label |
| Can Detected           | CAN FOUND / Rinse can     |
| Paper Detected         | PAPER FOUND / Fold paper  |
| General Waste Detected | GENERAL WASTE / Trash bin |

---

## 10. Implemented Functions

* Flask live camera streaming
* YOLO waste detection using `best.pt`
* PIR motion-based activation
* Camera and YOLO operation only during motion detection
* LCD output for system status
* LCD output for waste type and recycling guide
* DHT11 temperature and humidity measurement
* Idle mode environment display
* Raspberry Pi-based hardware and software integration

---

## 11. Troubleshooting

### DHT11 Sensor Reading Issue

The DHT11 sensor initially failed to read temperature and humidity values.

The issue was solved by connecting the SIG pin to GPIO4, physical pin 7, and updating the code to use:

```python
DHT_PIN = 4
```

After this change, temperature and humidity values were successfully displayed.

---

### Camera Frame Read Issue

OpenCV `VideoCapture(0)` failed to read camera frames.

The issue was solved by using Picamera2 instead of OpenCV VideoCapture.

---

### Flask Port Issue

When port 5000 was already in use, the previous process was terminated using:

```bash
sudo fuser -k 5000/tcp
```

Then the Flask server was restarted.

---

### YOLO Model Accuracy Issue

The default YOLO model did not detect waste objects accurately.

To improve detection, a waste detection dataset was used to fine-tune a custom YOLO model.
The trained `best.pt` model was then applied to the Raspberry Pi system.

---

## 12. Result Summary

As a result, we implemented a Raspberry Pi-based AIoT smart recycling prototype.

The system integrates motion detection, camera streaming, YOLO-based waste detection, LCD guidance, and temperature/humidity monitoring.

### Completed Functions

* PIR motion detection
* Flask camera streaming
* YOLO waste detection
* LCD recycling guide
* DHT11 temperature and humidity display
* Idle mode and active mode control

---

## 13. Limitations

* Detection accuracy can be affected by lighting conditions.
* Model performance depends on dataset quality.
* Raspberry Pi has limited computing power.
* Detection speed is slower than desktop GPU environments.
* More real waste images are needed to improve accuracy.

---

## 14. Future Work

* Improve the waste detection dataset
* Add LED indicators for each recycling bin
* Add detection history storage
* Improve Flask web dashboard
* Optimize YOLO model for faster inference
* Add more waste categories
* Improve hardware case design

---

## 15. My Contribution

I was responsible for Raspberry Pi sensor wiring, main application development, and YOLO fine-tuning.

### Main Contributions

* Connected sensors and modules to Raspberry Pi
* Tested PIR sensor, DHT11 sensor, LCD, and camera
* Developed the main `app.py` code
* Integrated Flask, Picamera2, YOLO, PIR, DHT11, and LCD
* Fine-tuned the YOLO model using a waste detection dataset
* Applied the trained `best.pt` model to Raspberry Pi
* Debugged sensor, camera, and Flask issues

---

## 16. Team Roles

| Member   | Role                                                               |
| -------- | ------------------------------------------------------------------ |
| 김서연     | Raspberry Pi sensor wiring, `app.py` development, YOLO fine-tuning |
| 장원준 |                           |


---

## 17. Conclusion

This project demonstrates a working AIoT smart recycling prototype.

The system detects user motion, activates the camera, classifies waste using YOLO, and provides recycling guidance through the LCD.

During idle mode, the system displays temperature and humidity using the DHT11 sensor.

Through this project, we implemented a practical prototype that combines AI vision, IoT sensors, and real-time user feedback.
