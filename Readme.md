# Face Detection Project

A comprehensive face detection and analysis system built with microservices architecture. This project provides capabilities for face detection, age and gender estimation, facial landmark detection, and image processing.

---

## 🧠 Overview

This microservices-based project enables advanced face analysis using AI models. It integrates multiple services to perform face detection, age and gender prediction, landmark detection, and persistent storage of results. Each service communicates via gRPC using Protocol Buffers.

---

## 🧩 Services

### 1. Image Input Service (`/ImageInputService`)
- Accepts and preprocesses user-uploaded images
- Validates input format and dimensions
- Sends the preprocessed image to downstream services

### 2. Age and Gender Estimation Service (`/AgeGenderEstimitionService`)
- Estimates the age and gender of detected faces
- Provides real-time analysis capabilities

### 3. Face Landmark Detection Service (`/FaceLandmarkDetectionService`)
- Detects facial landmarks and features
- Provides detailed facial geometry analysis

### 4. Data Storage Service (`/DataStorageService`)
- Handles persistent storage of face detection results
- Manages data retention and retrieval

---

## 📦 Protocol Buffers

The project uses Protocol Buffers for service communication:

- [`aggregator.proto`](./aggregator.proto): Defines aggregation service interfaces  
- [`save.proto`](./save.proto): Defines data saving protocols

---

## 🛠️ Setup and Installation

Each service can be run independently and has its own virtual environment. Follow the steps below for setting up environments and installing dependencies.

### 🔧 1. Main Project Virtual Environment

```bash
# Navigate to the root of the project
cd .\FaceDetectionProject

# Create the virtual environment
python -m venv venv

# Activate it
venv\Scripts\activate  # On Windows
# source venv/bin/activate  # On Unix/macOS

# Install dependencies
pip install -r requirements.main.txt

```

### 🔧 2. Face Landmark Service Virtual Environment

```bash
# Navigate to the service directory
cd .\FaceDetectionProject\FaceLandmarkDetectionService

# Create the virtual environment
python -m venv facevenv

# Activate it
facevenv\Scripts\activate  # On Windows
# source facevenv/bin/activate  # On Unix/macOS

# Install dependencies
pip install -r requirements.landmarks.txt
```
