# Copyright 2023 The MediaPipe Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Main scripts to run face landmarker."""

'''vdms servers - 10.8.1.200 10.8.1.201'''

import argparse
import sys
import time
from datetime import datetime, timezone, date
import os

from picamera2 import Picamera2
import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from PIL import Image

import vdms
import json

mp_face_mesh = mp.solutions.face_mesh
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles

# Global variables to calculate FPS
COUNTER, FPS = 0, 0
START_TIME = time.time()
DETECTION_RESULT = None

def run(model: str, num_faces: int,
        min_face_detection_confidence: float,
        min_face_presence_confidence: float, min_tracking_confidence: float,
        camera_id: int, width: int, height: int, record_duration: int,
        frame_rate: int) -> None:
    """Continuously run inference on images acquired from the camera and save them as JPG files.

    Args:
        model: Name of the face landmarker model bundle.
        num_faces: Max number of faces that can be detected by the landmarker.
        min_face_detection_confidence: The minimum confidence score for face
            detection to be considered successful.
        min_face_presence_confidence: The minimum confidence score of face
            presence score in the face landmark detection.
        min_tracking_confidence: The minimum confidence score for the face
            tracking to be considered successful.
        camera_id: The camera id to be passed to OpenCV.
        width: The width of the frame captured from the camera.
        height: The height of the frame captured from the camera.
        frame_rate: The frame rate for saving images.
    """
    #Connext to VDMS Server
    db = vdms.vdms()
    db.connect("10.8.1.200", 55555)

    # Start capturing video input from the camera
    picam2 = Picamera2()
    picam2.configure(picam2.create_preview_configuration(main={"format": 'RGB888', "size": (width, height)}))
    picam2.start()
    f = open("output.txt", "w")

    # Create output directory for images
    output_dir = "captured_images"
    os.makedirs(output_dir, exist_ok=True)

    end_time = time.time() + record_duration
        
    # Visualization parameters
    row_size = 50  # pixels
    left_margin = 24  # pixels
    text_color = (0, 0, 0)  # black
    font_size = 1
    font_thickness = 1
    fps_avg_frame_count = 10

    # Label box parameters
    label_background_color = (255, 255, 255)  # White
    label_padding_width = 1500  # pixels
    
    def save_result(result: vision.FaceLandmarkerResult,
                    unused_output_image: mp.Image, timestamp_ms: int):
        global FPS, COUNTER, START_TIME, DETECTION_RESULT

        # Calculate the FPS
        if COUNTER % fps_avg_frame_count == 0:
            FPS = fps_avg_frame_count / (time.time() - START_TIME)
            START_TIME = time.time()

        DETECTION_RESULT = result
        COUNTER += 1

    # Initialize the face landmarker model
    base_options = python.BaseOptions(model_asset_path=model)
    options = vision.FaceLandmarkerOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.LIVE_STREAM,
        num_faces=num_faces,
        min_face_detection_confidence=min_face_detection_confidence,
        min_face_presence_confidence=min_face_presence_confidence,
        min_tracking_confidence=min_tracking_confidence,
        output_face_blendshapes=True,
        result_callback=save_result)
    detector = vision.FaceLandmarker.create_from_options(options)

    # Time between image captures
    capture_interval = 1 / frame_rate

    # Continuously capture images from the camera and run inference
    try:
        while time.time() < end_time:
            start_time = time.time()
            image = picam2.capture_array()
            rgb_image = image
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_image)

            # Converting Image to Bytes
            image_data = mp_image.numpy_view()
            success, png_bytes = cv2.imencode('.png', image_data)
            png_bytes = png_bytes.tobytes()
#            pil_image.save(byte_io, format='JPG')
#            png_bytes = byte_io.getvalue()

            # Run face landmarker using the model
            detector.detect_async(mp_image, time.time_ns() // 1_000_000)

            # Save the image at the specified frame rate
            image_filename = os.path.join(output_dir, f'image_{datetime.now().strftime("%Y%m%d_%H%M%S")}.jpg')
            cv2.imwrite(image_filename, image)

            #Save image to VDMS
            blob_arr = []
            blob_arr.append(png_bytes)

            all_queries = []
#            addImage = {}

            props = {}
            props["ID"] = "ss1"
            props["Timestamp"] = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            props["Landmark"] = str(DETECTION_RESULT)
            props["Date"] = str(date.today())
            props["Data"] = "YES"

            addImage = {}
            addImage["format"] = "jpg"
            addImage["properties"] = props

            query = {}
            query["AddImage"] = addImage

            all_queries.append(query)

            print("Query Sent:")
            print(all_queries)
            
            response, res_arr = db.query(all_queries, [blob_arr])
            
            print("Response:")
            print(response, res_arr)

            f.write(datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3])
            f.write(" ")
            f.write(str(DETECTION_RESULT))
            f.write("\n")
            
            # Wait for the remaining time to meet the desired frame rate
            elapsed_time = time.time() - start_time
            if elapsed_time < capture_interval:
                time.sleep(capture_interval - elapsed_time)


    except KeyboardInterrupt:
        pass

    detector.close()
    cv2.destroyAllWindows()
    f.close()

def main():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '--model',
        help='Name of face landmarker model.',
        required=False,
        default='face_landmarker.task')
    parser.add_argument(
        '--numFaces',
        help='Max number of faces that can be detected by the landmarker.',
        required=False,
        default=1)
    parser.add_argument(
        '--minFaceDetectionConfidence',
        help='The minimum confidence score for face detection to be considered '
             'successful.',
        required=False,
        default=0.1)
    parser.add_argument(
        '--minFacePresenceConfidence',
        help='The minimum confidence score of face presence score in the face '
             'landmark detection.',
        required=False,
        default=0.1)
    parser.add_argument(
        '--minTrackingConfidence',
        help='The minimum confidence score for the face tracking to be '
             'considered successful.',
        required=False,
        default=0.5)
    parser.add_argument(
        '--cameraId', help='Id of camera.', required=False, default=0)
    parser.add_argument(
        '--frameWidth',
        help='Width of frame to capture from camera.',
        required=False,
        default=4656)
    parser.add_argument(
        '--frameHeight',
        help='Height of frame to capture from camera.',
        required=False,
        default=3496)
    parser.add_argument(
        '--recordDuration',
        help='Duration in seconds for which to record the images.',
        required=False,
        default=60 * 60)  # Default to 15 minutes
    parser.add_argument(
        '--fps',
        help='Frame rate for saving images.',
        required=False,
        default=1)  # Default to 1 frame per second
    args = parser.parse_args()

    run(args.model, int(args.numFaces), args.minFaceDetectionConfidence,
        args.minFacePresenceConfidence, args.minTrackingConfidence,
        int(args.cameraId), args.frameWidth, args.frameHeight,
        int(args.recordDuration), int(args.fps))

if __name__ == '__main__':
    main()
