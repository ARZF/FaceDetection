import tensorflow as tf

print("TensorFlow version:", tf.__version__)

# Optional: Check for GPU availability (will only work if prerequisites are met)
gpu_devices = tf.config.list_physical_devices('GPU')
if gpu_devices:
    print("GPU available:", gpu_devices)
else:
    print("GPU not available or prerequisites not met.")

exit() # Exit the Python interpreter
