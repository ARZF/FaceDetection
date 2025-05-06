from concurrent import futures
import grpc
import aggregator_pb2_grpc
import aggregator_pb2
import redis
import json
import traceback
from datetime import datetime
import save_pb2_grpc
import save_pb2
import insightface
from insightface.app import FaceAnalysis
import cv2
import numpy as np

# Initialize the face analysis model (InsightFace)
try:
    app = FaceAnalysis(name='buffalo_l')
    app.prepare(ctx_id=0, det_size=(640, 640))  # Using CPU (ctx_id=0)
    print("[LANDMARK] InsightFace model loaded successfully")
except Exception as e:
    print(f"[LANDMARK] ERROR initializing InsightFace: {str(e)}")
    traceback.print_exc()

# Redis client
redis_client = redis.Redis(host='localhost', port=6379, db=0)

# gRPC stub to storage service
try:
    channel = grpc.insecure_channel("localhost:50053")
    data_storage_stub = save_pb2_grpc.saveStub(channel)
    print("[LANDMARK] Connected to storage service")
except Exception as e:
    print(f"[LANDMARK] ERROR connecting to storage service: {str(e)}")
    data_storage_stub = None

class FaceLandmarkProcessing(aggregator_pb2_grpc.AggregatorServicer):
    def SaveFaceAttributes(self, request, context):
        print(f"[LANDMARK] Received image with key: {request.redis_key}")
        
        try:
            # Check if Redis key exists
            redis_face_key = request.redis_key
            redis_data = redis_client.get(redis_face_key)
            
            if redis_data:
                data = json.loads(redis_data.decode('utf-8'))
                print(f"[LANDMARK] Found existing data for {redis_face_key}")
            else:
                data = {}
                print(f"[LANDMARK] No existing data found for {redis_face_key}")

            # Decode image from request.frame
            if request.frame:
                nparr = np.frombuffer(request.frame, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if img is None:
                    print("[LANDMARK] Failed to decode image")
                    return aggregator_pb2.FaceResultResponse(response=False)
            else:
                print("[LANDMARK] No frame data received")
                return aggregator_pb2.FaceResultResponse(response=False)

            # Perform face landmark detection using InsightFace
            faces = app.get(img)

            if not faces or len(faces) == 0:
                print("[LANDMARK] No faces detected")
                return aggregator_pb2.FaceResultResponse(response=False)


            # Get landmarks from the first detected face
            if hasattr(faces[0], 'landmark_2d_106') :
                landmarks = faces[0].landmark_2d_106
                landmarks_dict = {f"point_{i}": [int(x), int(y)] for i, (x, y) in enumerate(landmarks)}
            else:
                print("[LANDMARK] 2D landmarks not found")
                print(f"[LANDMARK] Available face attributes: {dir(faces[0])}")
                landmarks_dict = {}
            

            # Store landmarks in data dictionary and save to Redis
            data["landmarks"] = landmarks_dict
            redis_client.set(redis_face_key, json.dumps(data))


            # Flag that landmarks are done
            redis_client.set(f"{redis_face_key}_landmarks_done", "True")
            print(f"[LANDMARK] Landmarks stored and flag set for {redis_face_key}")

            # Check if age/gender are already present
            if "age" in data and "gender" in data:
                print(f"[LANDMARK] Age/Gender already present. Forwarding to storage.")
                self.send_to_data_storage_service(data_storage_stub, redis_face_key, data["age"], data["gender"])

            return aggregator_pb2.FaceResultResponse(response=True)
            
        except Exception as e:
            print(f"[LANDMARK] ERROR processing image: {str(e)}")
            traceback.print_exc()
            return aggregator_pb2.FaceResultResponse(response=False)

    def send_to_data_storage_service(self, data_storage_stub, redis_key, age, gender):
        if data_storage_stub is None:
            print("[LANDMARK] Storage service stub is not available")
            return None
            
        try:
            response = data_storage_stub.SaveAgeGender(save_pb2.AgeGender(
                redis_key=redis_key,
                age=age,
                gender=gender
            ))
            print(f"[LANDMARK] Sent to storage. Response: {response.response}")
            return response
        except grpc.RpcError as e:
            print(f"[LANDMARK] Storage service error: {e.code()}: {e.details()}")
            return None
        except Exception as e:
            print(f"[LANDMARK] Unexpected error sending to storage: {str(e)}")
            traceback.print_exc()
            return None

def serve():
    try:
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        aggregator_pb2_grpc.add_AggregatorServicer_to_server(FaceLandmarkProcessing(), server)
        server.add_insecure_port('0.0.0.0:50051')
        server.start()
        print("[LANDMARK] Server started on port 50051")
        server.wait_for_termination()
    except Exception as e:
        print(f"[LANDMARK] ERROR starting server: {str(e)}")
        traceback.print_exc()

if __name__ == '__main__':
    serve()