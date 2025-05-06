from concurrent import futures
import grpc
import save_pb2_grpc
import json
import os
from datetime import datetime

class createOutputClass(save_pb2_grpc.saveServicer):
    def __init__(self):
        # Create output directory if it doesn't exist
        self.output_dir = "output_data"
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Initialize the main JSON data structure
        self.json_data = {}
        self.json_file_path = os.path.join(self.output_dir, "face_analysis_results.json")
        
        # Load existing data if file exists
        if os.path.exists(self.json_file_path):
            try:
                with open(self.json_file_path, 'r') as f:
                    self.json_data = json.load(f)
            except json.JSONDecodeError:
                # If file is corrupted, start with empty dict
                self.json_data = {}
        
    def SaveAgeGender(self, request, context):
        try:
            print(f"[AGE/GENDER] Received image with key: {request.redis_key}")
            print(f"[AGE/GENDER]: {request.age}, {request.gender}")
            
            # Add data to JSON structure
            timestamp = datetime.now().isoformat()
            
            # Create entry if key doesn't exist
            if request.redis_key not in self.json_data:
                self.json_data[request.redis_key] = {
                    "timestamp": timestamp,
                    "face_analysis": {}
                }
            
            # Update with age/gender info
            self.json_data[request.redis_key]["face_analysis"].update({
                "age": request.age,
                "gender": request.gender
            })
            
            # Save JSON file
            self._save_json_data()
            
        except Exception as e:
            print(f"[ERROR] Processing failed: {e}")
            
        return save_pb2_grpc.AgeGenderResponse(response=True)
    
    def SaveFaceLandmark(self, request, context):
        try:
            print(f"[FACE_LANDMARK] Received data with key: {request.redis_key}")
            
            # Add data to JSON structure
            timestamp = datetime.now().isoformat()
            
            # Create entry if key doesn't exist
            if request.redis_key not in self.json_data:
                self.json_data[request.redis_key] = {
                    "timestamp": timestamp,
                    "face_analysis": {}
                }
            
            # Update with landmark info
            landmarks = {}
            # Extract landmark data from request
            # Assuming your proto has landmarks defined, adjust based on your actual proto definition
            for field in request.DESCRIPTOR.fields:
                if field.name != "redis_key":  # Skip the key field
                    field_value = getattr(request, field.name)
                    landmarks[field.name] = field_value
            
            self.json_data[request.redis_key]["face_analysis"]["landmarks"] = landmarks
            
            # Save JSON file
            self._save_json_data()
            
        except Exception as e:
            print(f"[ERROR] Face landmark processing failed: {e}")
            
        return save_pb2_grpc.FaceLandmarkResponse(response=True)
    
    def _save_json_data(self):
        """Helper method to save the JSON data to file"""
        try:
            with open(self.json_file_path, 'w') as f:
                json.dump(self.json_data, f, indent=4)
            print(f"[INFO] Successfully saved data to {self.json_file_path}")
        except Exception as e:
            print(f"[ERROR] Failed to save JSON: {e}")

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    save_pb2_grpc.add_saveServicer_to_server(createOutputClass(), server)
    server.add_insecure_port('0.0.0.0:50053')
    print("[INFO] Server started on port 50053")
    server.start()
    server.wait_for_termination()

if __name__ == '__main__':
    serve()