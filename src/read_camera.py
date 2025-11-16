import os, threading
import time
from datetime import datetime
from picamera2 import Picamera2

class Camera:
    def __init__(self):
        self.camera = None
        self.photo_dir = 'images'
        self.photo_path = None

        os.makedirs(self.photo_dir, exist_ok=True)

    def capture_photo(self, exit_event: threading.Event):
        while not exit_event.is_set():
            try:
                if not self.camera:
                    self.camera = Picamera2()
                    camera_config = self.camera.create_still_configuration(
                        main={'size': (1920, 1080)},
                        controls={
                            'AeEnable': True,
                            'AwbEnable': True
                        }
                    )
                    self.camera.configure(camera_config)
                    
                self.camera.start()
                time.sleep(0.015)
                print("[Camera] Initialized")

                timestamp = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
                self.photo_path = os.path.join(self.photo_dir, f"plant_{timestamp}.jpg")
                self.camera.capture_file(self.photo_path)
                print('Taken!')

                self.camera.stop()
                time.sleep(1)

            except Exception as e:
                print(e)
                return None

exit_event = threading.Event()
cam = Camera()
cam_thread = threading.Thread(target=cam.capture_photo, args=(exit_event,), daemon=True)
cam_thread.start()

try:
    while True:
        print(cam.photo_path)
        time.sleep(1)
except KeyboardInterrupt:
    exit_event.set()
    cam.camera.stop()
    cam_thread.join(timeout=1)
