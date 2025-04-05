import cv2
import numpy as np
import face_recognition
import os
from typing import List, Tuple

class FaceAnalyzer:
    def __init__(self, training_images_path: str = 'Training images'):
        self.training_images_path = training_images_path
        self.known_face_encodings = []
        self.known_face_names = []
        self._load_known_faces()

    def _load_known_faces(self):
        """Load and encode all known faces from the training images directory"""
        images = []
        class_names = []
        
        for img_name in os.listdir(self.training_images_path):
            cur_img = cv2.imread(os.path.join(self.training_images_path, img_name))
            if cur_img is not None:
                images.append(cur_img)
                class_names.append(os.path.splitext(img_name)[0])

        self.known_face_encodings = self._find_encodings(images)
        self.known_face_names = class_names

    def _find_encodings(self, images: List[np.ndarray]) -> List[np.ndarray]:
        """Convert images to face encodings"""
        encode_list = []
        for img in images:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            try:
                encode = face_recognition.face_encodings(img)[0]
                encode_list.append(encode)
            except IndexError:
                continue
        return encode_list

    def recognize_faces(self, frame: np.ndarray) -> List[Tuple[str, Tuple[int, int, int, int]]]:
        """
        Recognize faces in a frame and return list of (name, location) tuples
        """
        # Resize frame for faster processing
        small_frame = cv2.resize(frame, (0, 0), None, 0.25, 0.25)
        small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

        # Find all faces in the current frame
        face_locations = face_recognition.face_locations(small_frame)
        face_encodings = face_recognition.face_encodings(small_frame, face_locations)

        results = []
        for face_encoding, face_location in zip(face_encodings, face_locations):
            # Compare with known faces
            matches = face_recognition.compare_faces(self.known_face_encodings, face_encoding)
            face_distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)
            best_match_index = np.argmin(face_distances)

            if matches[best_match_index] and face_distances[best_match_index] < 0.50:
                name = self.known_face_names[best_match_index].upper()
            else:
                name = "Unknown"

            # Scale face location back to original size
            y1, x2, y2, x1 = face_location
            y1, x2, y2, x1 = y1 * 4, x2 * 4, y2 * 4, x1 * 4
            results.append((name, (x1, y1, x2, y2)))

        return results 