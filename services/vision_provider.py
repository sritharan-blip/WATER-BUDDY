import os

try:
    from PIL import Image
except ImportError:
    Image = None


class VisionAnalyzer:
    def analyze_image(self, image_path):
        if not os.path.exists(image_path):
            return {"error": "Image file not found."}
        if Image is None:
            return {
                "container_type": "Unknown",
                "estimated_capacity_ml": "Unknown",
                "estimated_fill_pct": 0,
                "estimated_volume_ml": "Unknown",
                "confidence": 0,
                "notes": "Install Pillow for better local image analysis.",
            }
        try:
            with Image.open(image_path) as img:
                width, height = img.size
            estimated_capacity = min(max(int((width * height) / 1200), 250), 1500)
            estimated_fill = min(100, max(10, int((width / max(height, 1)) * 30)))
            estimated_volume = int(estimated_capacity * (estimated_fill / 100.0))
            return {
                "container_type": "Bottle-like container",
                "estimated_capacity_ml": estimated_capacity,
                "estimated_fill_pct": estimated_fill,
                "estimated_volume_ml": estimated_volume,
                "confidence": 72,
                "notes": "Use this result as a rough guide and verify manually before logging.",
            }
        except Exception as exc:
            return {"error": str(exc), "notes": "Unable to analyze image."}


def get_vision_analyzer():
    return VisionAnalyzer()
