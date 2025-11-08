### Downloading YOLO Models

Before using the service, you need to download the YOLO models. The service looks for models in the following directories:
- The current directory where the service is running
- A `models` subdirectory

Create a models directory and download some common models:

```bash
# Create models directory
mkdir models

# Download YOLOv8n for basic object detection
curl -L https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt -o models/yolov8n.pt

# Download YOLOv8n-seg for segmentation
curl -L https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n-seg.pt -o models/yolov8n-seg.pt

# Download YOLOv8n-cls for classification
curl -L https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n-cls.pt -o models/yolov8n-cls.pt

# Download YOLOv8n-pose for pose estimation
curl -L https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n-pose.pt -o models/yolov8n-pose.pt
```

For Windows PowerShell users:
```powershell
# Create models directory
mkdir models

# Download models using Invoke-WebRequest
Invoke-WebRequest -Uri "https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt" -OutFile "models/yolov8n.pt"
Invoke-WebRequest -Uri "https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n-seg.pt" -OutFile "models/yolov8n-seg.pt"
Invoke-WebRequest -Uri "https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n-cls.pt" -OutFile "models/yolov8n-cls.pt"
Invoke-WebRequest -Uri "https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n-pose.pt" -OutFile "models/yolov8n-pose.pt"
```
