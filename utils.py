import cv2
import numpy as np


def embedding_to_bytes(embedding):
    return embedding.astype(np.float32).tobytes()

def draw_face_box(image,face,label,recognized=True):
    x, y, w, h = face[:4].astype(int)
    if recognized:
        color = (0, 255, 0)
    else:
        color = (0, 0, 255)
    cv2.rectangle(
        image,
        (x, y),
        (x + w, y + h),
        color,
        2
    )
    if label:
        text_y = max(25,y-10)
        cv2.putText(
            image,
            label,
            (x, text_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            color,
            2
        )
    return image