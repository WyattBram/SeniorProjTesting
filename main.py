from ultralytics import YOLO
import cv2
from pathlib import Path
 

def predict(image_path: str = "ab.jpg"):
    model = YOLO("FinalModel.pt", task="detect") 

    results = model.predict(source=image_path, save=True, show=False)

    out_dir = Path(results[0].save_dir)
    print(f"Results saved to: {out_dir}")
    
    # Extract detection information
    result = results[0]  # Get first (and only) result
    
    # Get detection data
    confidences = result.boxes.conf if result.boxes is not None else []  # Confidence scores
    confidences = [x for x in confidences if x >.5]
    return len(confidences)


if __name__ == "__main__":
    predict()