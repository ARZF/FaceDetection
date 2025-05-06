from concurrent import futures
import grpc
import aggregator_pb2_grpc
import aggregator_pb2
import redis
import cv2
import numpy as np
from deepface import DeepFace
from datetime import datetime
import save_pb2_grpc
import save_pb2
import json
import traceback

# Initialize Redis client
redis_client = redis.Redis(host='localhost', port=6379, db=0)

# Connect to data storage service
try:
    channel = grpc.insecure_channel("localhost:50053")  
    data_storage_stub = save_pb2_grpc.saveStub(channel)
    print("[AGE/GENDER] Connected to data storage service")
except Exception as e:
    print(f"[AGE/GENDER] Error connecting to data storage service: {e}")
    traceback.print_exc()
    data_storage_stub = None

# Connect to landmark service
try:
    landmark_channel = grpc.insecure_channel("localhost:50051")
    landmark_stub = aggregator_pb2_grpc.AggregatorStub(landmark_channel)
    print("[AGE/GENDER] Connected to landmark service")
except Exception as e:
    print(f"[AGE/GENDER] Error connecting to landmark service: {e}")
    traceback.print_exc()
    landmark_stub = None

class AgeGenderImageProcessing(aggregator_pb2_grpc.AggregatorServicer):
    def SaveFaceAttributes(self, request, context):
        print(f"[AGE/GENDER] Received image with key: {request.redis_key}")
        
        try:
            # Check if this request already has results in Redis
            redis_response = redis_client.get(request.redis_key)

            if redis_response:
                try:
                    data = json.loads(redis_response.decode('utf-8'))
                    if "age" in data and "gender" in data:
                        age = data["age"]
                        gender = data["gender"]
                        send_to_data_storage_service(data_storage_stub, request.redis_key, age, gender)
                        return aggregator_pb2.FaceResultResponse(response=True)
                    else:
                        print(f"[AGE/GENDER] 'age' or 'gender' missing in Redis data: {data}")
                except Exception as e:
                    print(f"[ERROR] Failed to parse Redis response: {e}")
                    traceback.print_exc()
                    return aggregator_pb2.FaceResultResponse(response=False)

            # Process the image if no cache hit
            nparr = np.frombuffer(request.frame, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                print("[AGE/GENDER] Failed to decode image")
                return aggregator_pb2.FaceResultResponse(response=False)

            try:
                analysis_list = DeepFace.analyze(
                    img_path=img,
                    actions=["age", "gender"],
                    detector_backend="retinaface",
                    enforce_detection=False
                )

                # Process each face detected
                for idx, analysis in enumerate(analysis_list):
                    age = int(analysis['age'])
                    gender = max(analysis['gender'], key=analysis['gender'].get) if isinstance(analysis['gender'], dict) else analysis['gender']

                    print(f"[AGE/GENDER] Face {idx+1}: Estimated Age: {age}, Gender: {gender}")

                    # Create a unique Redis key for this face
                    redis_face_key = f"{request.redis_key}_face{idx+1}"
                    
                    # Check if data already exists for this face
                    existing_data = redis_client.get(redis_face_key)
                    if existing_data:
                        face_data = json.loads(existing_data.decode('utf-8'))
                    else:
                        face_data = {}
                    
                    # Update with age and gender data
                    face_data["age"] = age
                    face_data["gender"] = gender
                    
                    # Save to Redis
                    redis_client.set(redis_face_key, json.dumps(face_data))
                    
                    # Set flag that age/gender processing is done
                    redis_client.set(f"{redis_face_key}_age_gender_done", "True")
                    print(f"[AGE/GENDER] Age/Gender processed and flag set for {redis_face_key}")

                    # Check if landmarks are already processed
                    landmarks_done_key = f"{redis_face_key}_landmarks_done"
                    if redis_client.exists(landmarks_done_key):
                        print(f"[AGE/GENDER] Landmarks already processed for {redis_face_key}. Sending to data storage.")
                        send_to_data_storage_service(data_storage_stub, redis_face_key, age, gender)
                    else:
                        print(f"[AGE/GENDER] Triggering landmark service for {redis_face_key}")
                        try:
                            if landmark_stub:
                                landmark_response = landmark_stub.SaveFaceAttributes(aggregator_pb2.FaceResult(
                                    frame=request.frame,
                                    redis_key=redis_face_key
                                ))
                                print(f"[AGE/GENDER] Landmark service responded: {landmark_response.response}")
                            else:
                                print("[AGE/GENDER] Cannot trigger landmark service - connection not available")
                        except grpc.RpcError as e:
                            print(f"[AGE/GENDER] Error calling landmark service: {e.code()}: {e.details()}")
                        except Exception as e:
                            print(f"[AGE/GENDER] Unexpected error calling landmark service: {e}")
                            traceback.print_exc()

                return aggregator_pb2.FaceResultResponse(response=True)
                
            except Exception as e:
                print(f"[ERROR] DeepFace failed: {e}")
                traceback.print_exc()
                return aggregator_pb2.FaceResultResponse(response=False)
                
        except Exception as e:
            print(f"[AGE/GENDER] Unexpected error: {e}")
            traceback.print_exc()
            return aggregator_pb2.FaceResultResponse(response=False)
    
def send_to_data_storage_service(data_storage_stub, redis_key, age, gender):  
    if data_storage_stub is None:
        print("[AGE/GENDER] Data storage service not available")
        return None
        
    try:
        response = data_storage_stub.SaveAgeGender(save_pb2.AgeGender(
            redis_key=redis_key,
            age=age,
            gender=gender
        ))
        print(f"[AGE/GENDER] Data storage response: {response.response}")
        return response
    except grpc.RpcError as e:
        print(f"[AGE/GENDER] Data storage service error: {e.code()}: {e.details()}")
        return None
    except Exception as e:
        print(f"[AGE/GENDER] Unexpected error sending to storage: {e}")
        traceback.print_exc()
        return None

def serve():
    try:
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        aggregator_pb2_grpc.add_AggregatorServicer_to_server(AgeGenderImageProcessing(), server)
        server.add_insecure_port('0.0.0.0:50052')
        server.start()
        print("[AGE/GENDER] Server started on port 50052")
        server.wait_for_termination()
    except Exception as e:
        print(f"[AGE/GENDER] Error starting server: {e}")
        traceback.print_exc()

if __name__ == '__main__':
    serve()