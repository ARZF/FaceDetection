import grpc
import os
from datetime import datetime
import hashlib
import aggregator_pb2
import aggregator_pb2_grpc

def load_images_from_folder(folder_path):
    for filename in os.listdir(folder_path):
        if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            filepath = os.path.join(folder_path, filename)
            with open(filepath, 'rb') as f:
                yield filename, f.read()

def compute_hash(image_bytes):
    return hashlib.sha256(image_bytes).hexdigest()

def create_grpc_stub(service_address):
    """Create and return a gRPC channel and stub"""
    channel = grpc.insecure_channel(service_address)
    return aggregator_pb2_grpc.AggregatorStub(channel), channel

def send_to_services(stub, image_bytes, redis_key, service_name):  
    try:
        response = stub.SaveFaceAttributes(aggregator_pb2.FaceResult(
            time=datetime.now().isoformat(),
            frame=image_bytes,
            redis_key=redis_key
        ))
        print(f"{service_name} response: {response.response}")
        return response
    except grpc.RpcError as e:
        print(f"{service_name} service error: {e.code()}: {e.details()}")
        return None
def main():
    SERVICES = {
    'age_gender': 'localhost:50052',
    'landmark': 'localhost:50051'
    }
    try:
        # Create stubs for all services
        stubs = {}
        channels = []
        for name, address in SERVICES.items():
            stub, channel = create_grpc_stub(address)
            stubs[name] = stub
            channels.append(channel)

        image_folder = os.path.join(os.path.dirname(__file__), "sample_image")
        
        for filename, image_bytes in load_images_from_folder(image_folder):
            redis_key = compute_hash(image_bytes)
            print(f"\nProcessing {filename} (key: {redis_key})")
            
            # Send to all services
            for service_name, stub in stubs.items():
                send_to_services(stub, image_bytes, redis_key, service_name)
    except Exception as e:
        print(f"Application error: {e}")
    finally:
        for channel in channels:
            channel.close()
if __name__ == "__main__":
    main()
