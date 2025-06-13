import cv2
import logging
import os
from collections import defaultdict
from ultralytics import YOLO
import numpy as np
import torch

from src.core import config

logger = logging.getLogger(__name__)


class DetectionModel:
    def __init__(self):
        self.model = self.load_model()
        self.labels = self.model.names
        self.total_objects = 0
        self.total_balls = 0
        self.hole_positions = [
            (0, 0),
            (config.output_dimensions[0] // 2, 0),
            (config.output_dimensions[0], 0),
            (0, config.output_dimensions[1]),
            (config.output_dimensions[0] // 2, config.output_dimensions[1]),
            (config.output_dimensions[0], config.output_dimensions[1]),
        ]
        self.frame_count = 0
        self.found_holes = []
        self.last_result = None

    def load_model(self):
        if not os.path.exists(config.detection_model_path):
            logger.error(
                f"Model file not found at {config.detection_model_path}.")
            return None
        else:
            device = "cuda" if torch.cuda.is_available() else "cpu"
            model = YOLO(config.detection_model_path, task="detect")
            model.to(device)
            return model

    # Can have as a trigger function to change the model during runtime. Not used yet, waiting for liveconfig to be updated.
    # @trigger
    def change_model(self, path=None):
        if path is None:
            path = config.detection_model_path
        if os.path.exists(path):
            logger.info(f"Loading model from {path}.")
            self.model = YOLO(path, task="detect")
        else:
            logger.error(
                f"Model file not found at {path}. Continuing with existing model.")
            return None

    def detect(self, frame):
        self.frame_count += 1
        if self.frame_count % config.process_every_n_frames != 0:
            return self.last_result, self.labels

        # Detect available device and optimize based on hardware
        device = "cuda" if torch.cuda.is_available() else "cpu"

        # Adjust settings based on device
        # For CPU: don't use half precision, lower batch size
        use_half = device == "cuda"

        results = self.model(
            frame,
            verbose=False,
            conf=config.conf_threshold,
            iou=0.40,
            device=device,
            half=use_half,
            stream=True
        )

        results = list(results)

        all_results = []
        if results is None or len(results) == 0 or results[0].boxes is None:
            return None, None

        all_results = [
            (r, self.labels[int(r.cls.item())])
            for result in results for r in result.boxes]

        all_results.sort(key=lambda x: x[0].conf.item(), reverse=True)

        filtered_results = self._filter_results(all_results)

        filtered_results_struct = results[0]
        filtered_results_struct.boxes = filtered_results
        self.last_result = (filtered_results_struct, )
        return self.last_result, self.labels

    def _filter_results(self, all_results):
        filtered_results = []
        self.found_holes = []
        counts = defaultdict(int)
        self.total_balls = 0

        class_limits = {
            "white": 1,
            "black": 1,
            "red": 7,
            "yellow": 7,
            "hole": 6,
            "arm": 3}

        for result, classname in all_results:
            _, _, xmin, ymin, xmax, ymax = self._get_result_info(result)
            area = (xmax - xmin) * (ymax - ymin)

            if classname in class_limits \
                    and counts[classname] < class_limits[classname]:

                if classname in {"white", "black", "red", "yellow"} \
                        and self._is_likely_ball(area):
                    counts[classname] += 1
                    filtered_results.append(result)
                    self.total_balls += 1

                elif classname == "hole" \
                        and self._is_likely_hole(xmin, ymin, xmax, ymax):
                    counts[classname] += 1
                    filtered_results.append(result)

                elif classname == "arm" \
                        and self._is_likely_arm(area):
                    counts[classname] += 1
                    filtered_results.append(result)

        return filtered_results

    def _is_likely_ball(self, area):
        return area > config.ball_area_range[0] \
            and area < config.ball_area_range[1]

    def _is_likely_arm(self, area):
        return area > config.arm_area_range[0] \
            and area < config.arm_area_range[1]

    def _is_likely_hole(self, xmin, ymin, xmax, ymax):
        middlex = int((xmin + xmax) / 2)
        middley = int((ymin + ymax) / 2)

        if self._is_near_existing_hole(middlex, middley):
            return False
        if self._hole_is_near_expected_position(middlex, middley):
            self.found_holes.append((middlex, middley))
            return True

    def _hole_is_near_expected_position(self, x, y):
        for hole in self.hole_positions:
            if abs(hole[0] - x) < config.hole_threshold \
                    and abs(hole[1] - y) < config.hole_threshold:
                return True
        return False

    def _is_near_existing_hole(self, x, y):
        for hole in self.found_holes:
            if abs(hole[0] - x) < config.hole_threshold \
                    and abs(hole[1] - y) < config.hole_threshold:
                return True
        return False

    def _get_result_info(self, result):
        xyxy = result.xyxy.cpu().numpy().squeeze().astype(int)
        classidx = int(result.cls.item())
        classname = self.labels[classidx]
        color = config.bbox_colors[classidx % len(config.bbox_colors)]

        return classname, color, xyxy[0], xyxy[1], xyxy[2], xyxy[3]

    def draw(self, frame, filtered_results):
        if not filtered_results or filtered_results[0].boxes is None:
            return

        boxes = filtered_results[0].boxes
        self.total_objects = 0

        object_data = []
        for result in boxes:
            classname, color, xmin, ymin, xmax, ymax = self._get_result_info(
                result)
            conf = result.conf.item()

            if conf > config.conf_threshold:
                object_data.append(
                    (classname, color, xmin, ymin, xmax, ymax, conf))

        for classname, color, xmin, ymin, xmax, ymax, conf in object_data:
            cv2.rectangle(frame, (xmin, ymin), (xmax, ymax), color, 2)
            cv2.circle(
                frame,
                ((xmin + xmax) // 2, (ymin + ymax) // 2),
                4, (0, 0, 255), -1)

            label = f"{classname}: {int(conf * 100)}%"
            label_size, _ = cv2.getTextSize(
                label,
                cv2.FONT_HERSHEY_SIMPLEX,
                config.font_scale,
                config.font_thickness)
            label_ymin = max(ymin, label_size[1] + 10)

            cv2.putText(
                frame,
                label,
                (xmin, label_ymin - 7),
                cv2.FONT_HERSHEY_SIMPLEX,
                config.font_scale,
                config.font_color,
                config.font_thickness)

            self.total_objects += 1

        summary_text = [
            f'Total number of objects: {self.total_objects}',
            f'Total number of balls: {self.total_balls}'
        ]
        for i, text in enumerate(summary_text):
            cv2.putText(
                frame,
                text, (120, 40 + i * 20),
                cv2.FONT_HERSHEY_SIMPLEX,
                config.font_scale,
                config.font_color,
                config.font_thickness)

        cv2.imshow("Detection", frame)

    def extract_bounding_boxes(self, frame, results):
        bounding_boxes = []
        if results is None or len(results) == 0:
            return None
        for result in results:
            for box in result.boxes:
                _, _, xmin, ymin, xmax, ymax = self._get_result_info(box)
                bounding_boxes.append((xmin, ymin, xmax, ymax))

        mask = np.zeros_like(frame[:, :, 0])
        for (xmin, ymin, xmax, ymax) in bounding_boxes:
            mask[ymin:ymax, xmin:xmax] = 255

        return cv2.inpaint(frame, mask, 3, cv2.INPAINT_TELEA)

    def handle_detection(self, frame):
        detections = None
        labels = None
        if not config.use_model:
            if not config.hide_windows:
                self.destroy_detection_drawing_window()
                cv2.imshow("Camera Frame", frame)
        else:
            detections, labels = self.detect(frame)
            if config.draw_results and not config.hide_windows:
                self.destroy_camera_frame_window()
                drawing_frame = frame.copy()
                self.draw(drawing_frame, detections)
                cv2.imshow("Detection", drawing_frame)
            elif not config.hide_windows:
                self.destroy_detection_drawing_window()
                cv2.imshow("Camera Frame", frame)
            elif config.hide_windows:
                cv2.destroyAllWindows()

        return detections, labels

    def destroy_camera_frame_window(self):
        try:
            if cv2.getWindowProperty("Camera Frame", cv2.WND_PROP_VISIBLE) >= 0:
                cv2.destroyWindow("Camera Frame")
        except cv2.error as e:
            pass

    def destroy_detection_drawing_window(self):
        try:
            if cv2.getWindowProperty("Detection", cv2.WND_PROP_VISIBLE) >= 0:
                cv2.destroyWindow("Detection")
        except cv2.error as e:
            pass
