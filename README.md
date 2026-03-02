# 🎭 Virsa FaceFinder

**Virsa FaceFinder** is an intelligent photo gallery platform that uses AI-powered face recognition to automatically identify and organize photos featuring specific people. Perfect for events, family gatherings, or any occasion where you want to find all photos of yourself effortlessly!

## 📑 Table of Contents

- [Features](#-features)
- [Architecture](#-architecture)
- [Branding & Color Scheme](#-branding--color-scheme)
- [Project Structure](#-project-structure)
- [System Requirements](#-system-requirements)
- [Quick Start](#-quick-start)
  - [Prerequisites](#prerequisites)
  - [Clone the Repository](#1-clone-the-repository)
  - [Environment Setup](#2-environment-setup)
  - [SSL Certificate Setup](#3-ssl-certificate-setup-https)
  - [Backend Setup](#4-backend-setup)
  - [Frontend Setup](#5-frontend-setup)
  - [Start Redis Server](#6-start-redis-server)
  - [Start Services](#7-start-services)
  - [Access the Application](#8-access-the-application)
  - [Known People Database Setup](#9-optional-set-up-known-people-database-linkedin-integration)
- [API Endpoints](#-api-endpoints)
- [Recent Updates](#-recent-improvements--updates)
- [Known People Management](#-known-people-management)
- [Photo Management](#-photo-management-features)
- [How It Works](#-how-it-works)
- [Database Schema](#-database-schema)
- [Background Tasks (Celery)](#-background-tasks-celery)
- [Face Recognition Module](#-face-recognition-module)
- [Testing](#-testing)
- [Troubleshooting](#-troubleshooting)
- [Debugging & Monitoring](#-debugging--monitoring)
- [Utility Scripts](#-utility-scripts)
- [Development Notes](#-development-notes)
- [Deployment](#-deployment)
- [FAQ](#-frequently-asked-questions-faq)
- [Contributing](#-contributing)
- [License](#-license)
- [Contributors](#-contributors)
- [Acknowledgments](#-acknowledgments)
- [Support](#-support)

## 🌟 Features

- **AI-Powered Face Recognition**: Upload reference photos and automatically find yourself in group photos
- **Smart Gallery Management**: Create and manage multiple photo galleries with real-time photo counts
- **Automatic Face Detection**: Automatically detects and tags faces in uploaded photos
- **User Profiles**: Personalized user accounts with intuitive reference photo management
- **Share Galleries**: Generate shareable links for your galleries with direct share token access
- **Background Processing**: Asynchronous face detection and recognition using Celery workers
- **Modern UI**: Clean, responsive React frontend with Tailwind CSS and new vibrant color scheme
- **Loading Indicators**: Visual feedback during photo navigation and view switching
- **Real-time Processing Status**: Monitor gallery processing progress in real-time
- **LinkedIn Profile Integration**: Automatically link identified people to their LinkedIn profiles
- **Known People Database**: Build a database of frequently recognized people with metadata
- **Photo Download**: Download individual or batch photos with smart filename generation
- **Photo Management**: Delete and manage photos in your galleries (owner only)
- **Auto-Tagging**: Automatically tag known people in uploaded photos with confidence scores

## 🏗️ Architecture

### Tech Stack

**Backend:**
- FastAPI (Python web framework)
- MongoDB Atlas (NoSQL database)
- Redis (Message broker for Celery)
- Celery (Background task processing)
- InsightFace (Face detection and embedding generation)
- Pinecone (Vector database for face embeddings)
- Local filesystem (Image storage)

**Frontend:**
- React.js with Vite (Lightning-fast build tool)
- React Router (Navigation and routing)
- Tailwind CSS (Styling with custom color palette)
- Lucide React (Beautiful icon library)
- Zustand (State management)
- Axios (HTTP client with interceptors)

## 🎨 Branding & Color Scheme

**Virsa FaceFinder** features a vibrant, modern design with a carefully chosen color palette:

- **Primary Color**: `#00CCB4` - Teal/Turquoise (Main buttons, links, and interactive elements)
- **Accent Color**: `#FF968C` - Coral/Salmon (Feature highlights and secondary accents)
- **Secondary Color**: `#EC9AE2` - Pink/Magenta (Special highlights and user avatars)
- **Logo**: VirsaAnimation.jpeg (Displayed in header and favicon)

All colors have extended palettes (50-900 shades) for Tailwind CSS, ensuring beautiful gradients and hover states throughout the interface.

## 📁 Project Structure

```
Face_Recognition_Gallery_Platform/
├── backend/
│   ├── api/
│   │   ├── routes/          # API endpoints (auth, galleries, photos)
│   │   └── auth_utils.py    # JWT authentication utilities
│   ├── config/
│   │   ├── settings.py      # Configuration and environment variables
│   │   └── database.py      # MongoDB connection setup
│   ├── models/
│   │   └── database.py      # MongoDB document schemas and helpers
│   ├── schemas/
│   │   └── schemas.py       # Pydantic request/response models
│   ├── services/
│   │   └── storage_service.py  # Local file storage service
│   ├── workers/
│   │   ├── celery_app.py    # Celery configuration
│   │   └── tasks.py         # Background tasks (face detection, recognition)
│   ├── face-recognition-module/  # Face detection and matching engine
│   │   ├── face_scanner.py  # Scans known_faces directory
│   │   ├── face_matcher.py  # Matches faces against database
│   │   └── known_people_db.py  # Known people database operations
│   ├── main.py              # FastAPI application entry point
│   ├── run.py               # Unified backend startup script
│   ├── scan_known_faces.py  # CLI tool for managing known people
│   ├── add_linkedin_profiles.py  # Script to add LinkedIn profiles
│   ├── sync_linkedin_to_matches.py  # Sync LinkedIn data to matches
│   └── requirements.txt     # Python dependencies
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── components/      # Reusable React components
│   │   │   └── PhotoViewer.jsx  # Photo viewer with LinkedIn links
│   │   ├── pages/          # Page components
│   │   │   └── GalleryPage.jsx  # Gallery with tagging features
│   │   ├── utils/
│   │   │   └── downloadUtils.js  # Photo download utilities
│   │   ├── App.js          # Main React app
│   │   └── index.js        # React entry point
│   └── package.json        # Node.js dependencies
├── storage/                # Local file storage
│   ├── galleries/          # Gallery photos
│   ├── reference/          # User reference photos
│   └── known_faces/        # Reference photos for known people
│       └── {PersonName}/    # Organized by person name
└── .env                    # Environment variables
```

## 💻 System Requirements

### Minimum Requirements
- **CPU**: Intel Core i5 / AMD Ryzen 5 or better (4+ cores recommended)
- **RAM**: 8 GB minimum, 16 GB recommended
- **GPU**: NVIDIA GPU with 4+ GB VRAM (for GPU acceleration)
  - Supported: GTX 1660, RTX 3060, RTX 3080, RTX 4090, or better
  - CUDA 11.8+ required
- **Storage**: 10 GB free space (20+ GB recommended for large galleries)
- **OS**: Windows 10/11, Ubuntu 20.04+, macOS 11+

### Recommended Production Configuration
- **CPU**: Intel Core i7 / AMD Ryzen 7 (8+ cores)
- **RAM**: 32 GB
- **GPU**: NVIDIA RTX 3080/4090 (10+ GB VRAM)
- **Storage**: SSD with 50+ GB free space
- **Network**: Stable internet connection for MongoDB Atlas and Pinecone

### Software Dependencies
- **Python**: 3.9, 3.10, or 3.11 (3.11 recommended)
- **Node.js**: 16.x or 18.x (18.x recommended)
- **Redis**: 6.x or 7.x
- **CUDA Toolkit**: 11.8 or 12.4 (if using GPU)
- **OpenSSL**: For generating SSL certificates

## 🚀 Quick Start

### Prerequisites

- Python 3.9+ (3.11+ recommended)
- Node.js 16+ (18+ recommended)
- Redis Server
- MongoDB Atlas account (or local MongoDB)
- Git (for version control)
- PyTorch with CUDA support (for GPU acceleration)

### 1. Clone the Repository

```bash
git clone <repository-url>
cd Face_Recognition_Gallery_Platform
```

### 2. Environment Setup

Create a `.env` file in the project root:

```env
# Database Configuration - MongoDB Atlas
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/
MONGODB_DB_NAME=aiGallery

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Celery Configuration
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Celery Worker Settings (Optional - auto-detects if not set)
# CELERY_CONCURRENCY=2            # Number of concurrent tasks (default: 2 for GPU workloads)
# CELERY_POOL_TYPE=gevent         # Pool type: gevent (Windows), prefork (Linux/Mac)

# Local Storage Configuration
STORAGE_BASE_PATH=storage
STORAGE_BASE_URL=https://recommendations.vosmos.events:7008/storage

# JWT Configuration
JWT_SECRET_KEY=your-super-secret-jwt-key-change-this-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=43200

# Application Configuration
ENVIRONMENT=development
DEBUG=true
CORS_ORIGINS=https://recommendations.vosmos.events:7003

# Face Recognition Configuration
FACE_DETECTION_THRESHOLD=0.5
MAX_FACES_PER_IMAGE=50

# Face Matching Configuration
FACE_MATCH_THRESHOLD=0.7
FACE_MATCH_TOP_K=10000

# Pinecone Configuration
PINECONE_API_KEY=your-pinecone-api-key
PINECONE_ENVIRONMENT=us-east-1-aws
PINECONE_INDEX_NAME=face-embeddings-webapp

# Optional: LinkedIn Integration
LINKEDIN_API_KEY=your-linkedin-api-key  # If using LinkedIn API integration
```

**Important Notes:**
- Replace `username:password` in `MONGODB_URI` with your actual MongoDB Atlas credentials
- Update `JWT_SECRET_KEY` with a strong random key for production
- Replace `your-pinecone-api-key` with your actual Pinecone API key
- Update domain `recommendations.vosmos.events` with your actual domain or use `localhost` for local development

### 3. SSL Certificate Setup (HTTPS)

The application uses HTTPS for secure communication. You'll need SSL certificates for development.

**Option 1: Generate Self-Signed Certificates (Development)**

```bash
# Create certs directory
mkdir certs
cd certs

# Generate self-signed certificate (valid for 365 days)
# Windows (PowerShell):
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes

# Linux/Mac:
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes

# When prompted, fill in the certificate details:
# Common Name (CN): localhost (or your domain like recommendations.vosmos.events)
cd ..
```

**Option 2: Use Existing Certificates (Production)**

Place your SSL certificates in the `certs/` directory:
- `certs/key.pem` - Private key
- `certs/cert.pem` - Certificate

**Important:** Add `certs/` to `.gitignore` to prevent committing private keys to version control.

### 4. Backend Setup

```bash
# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install PyTorch with CUDA support (for GPU acceleration)
# For CUDA 12.4 (check your CUDA version first with: nvidia-smi)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124

# Install other dependencies
pip install -r requirements.txt
```

**Note:** If you don't have a GPU or want CPU-only mode, install PyTorch without CUDA:
```bash
pip install torch torchvision torchaudio
```

### 5. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Create frontend .env file (optional - uses defaults from vite.config.js)
cp .env.example .env
```

### 6. Start Redis Server

Before starting the application, ensure Redis is running:

```bash
# Windows (if installed via Chocolatey or MSI):
redis-server

# Linux (Ubuntu/Debian):
sudo systemctl start redis
# or
redis-server

# Mac (if installed via Homebrew):
brew services start redis
# or
redis-server
```

Verify Redis is running:
```bash
redis-cli ping
# Should return: PONG
```

### 7. Start Services

You need **3 separate terminal windows** to see all logs clearly. Run all commands from the **project root directory**.

**Terminal 1 - Celery Worker (Background Task Processing):**
```bash
python backend/start_celery.py
```
*Handles face detection and recognition tasks asynchronously*

**Terminal 2 - FastAPI Backend (API Server):**
```bash
python run.py
```
*Runs pre-flight checks and starts the backend API server with HTTPS*

**Terminal 3 - React Frontend (Web UI):**
```bash
cd frontend
npm run dev
```
*Starts the Vite development server with hot module reloading*

**Important Notes:**
- All commands must be run from the project root directory (except frontend)
- Wait for each service to fully start before starting the next one
- Celery must be started before the backend to process tasks
- Check each terminal for any error messages during startup

### 8. Access the Application

**With Custom Domain (as configured):**
- **Frontend**: https://recommendations.vosmos.events:7003
- **Backend API**: https://recommendations.vosmos.events:7008
- **API Documentation**: https://recommendations.vosmos.events:7008/docs
- **Health Check**: https://recommendations.vosmos.events:7008/health

**With Localhost (for local development):**
- **Frontend**: https://localhost:7003
- **Backend API**: https://localhost:7008
- **API Documentation**: https://localhost:7008/docs
- **Health Check**: https://localhost:7008/health

**First-Time Access:**
- Your browser will warn about the self-signed certificate
- Click "Advanced" → "Proceed to site" (Chrome) or "Accept the Risk" (Firefox)
- This is normal for development with self-signed certificates

### 9. Optional: Set Up Known People Database (LinkedIn Integration)

To enable automatic LinkedIn profile linking for frequently recognized people:

**Step 1: Organize Reference Photos**
```bash
# Create known_faces directory if it doesn't exist
mkdir -p storage/known_faces

# Organize photos by person name
storage/known_faces/
├── John Smith/
│   ├── photo1.jpg
│   ├── photo2.jpg
│   └── photo3.jpg
├── Jane Doe/
│   ├── photo1.jpg
│   └── photo2.jpg
└── Bob Johnson/
    └── profile.jpg
```

**Step 2: Scan and Register Known Faces**
```bash
cd backend

# Scan known_faces directory and register people
python scan_known_faces.py --scan

# View all known people
python scan_known_faces.py --list
```

**Step 3: Add LinkedIn Profiles (Optional)**
```bash
# Add LinkedIn profiles to known people
python add_linkedin_profiles.py

# Sync LinkedIn data to match results
python sync_linkedin_to_matches.py
```

For detailed CLI options, see the [Known People Management](#-known-people-management) section below.

## 🔑 API Endpoints

### Authentication (`/api/auth`)
- `POST /register` - Register new user account
- `POST /login` - User login and get access token
- `GET /me` - Get current authenticated user info
- `POST /upload-reference-photos` - Upload reference photos for face recognition
- `POST /reupload-reference-photos` - Re-upload/update reference photos
- `GET /my-reference-photos` - Get all reference photos with URLs
- `DELETE /reference-photos/{photo_id}` - Delete a reference photo
- `POST /trigger-gallery-scan` - Manually trigger face matching across all galleries

### Galleries (`/api/galleries`)
- `GET /my-galleries` - Get all galleries hosted by current user (with accurate photo counts)
- `POST /create` - Create a new empty gallery
- `POST /upload` - Create gallery and upload photos in one request
- `GET /{share_token}` - Get gallery details by share token
- `POST /{gallery_id}/add-photos` - Add more photos to existing gallery
- `GET /{share_token}/all-photos` - Get all photos in gallery with pagination
- `GET /{share_token}/my-photos-with-confidence` - Get photos with recognized user faces
- `POST /{share_token}/tag-known-people` - Trigger tagging of known people in gallery
- `GET /{share_token}/status` - Get gallery processing status
- `DELETE /{share_token}/photos/{photo_id}` - Delete a photo from gallery

### Features
- **Real-time Photo Counts**: Gallery counts are dynamically calculated from the database
- **Pagination**: Support for paginated photo retrieval (50 photos per page by default)
- **Processing Status**: Real-time feedback on gallery and photo processing progress
- **Tagged People**: Photos include tagged known people with confidence scores and LinkedIn links

## 📋 Recent Improvements & Updates

### Version 2.2 - HTTPS & Production Enhancements (Latest)
- ✅ **HTTPS Support**: Full SSL/TLS encryption for secure communication
- ✅ **Custom Domain Support**: Configured for `recommendations.vosmos.events`
- ✅ **Self-Signed Certificate Setup**: Easy development environment setup
- ✅ **GPU-Optimized Celery**: Reduced concurrency to prevent GPU memory overflow
- ✅ **Enhanced Environment Variables**: Comprehensive configuration options
- ✅ **Improved Startup Scripts**: Better pre-flight checks and error handling
- ✅ **Port Configuration**: Backend (7008), Frontend (7003) with CORS support

### Version 2.1 - LinkedIn Integration & Advanced Features
- ✅ **LinkedIn Profile Integration**: Automatically link identified people to LinkedIn profiles
- ✅ **Known People Database**: Comprehensive database for frequently recognized individuals
- ✅ **Photo Download**: Download individual or batch photos with smart filename generation
- ✅ **Auto-Tagging**: Automatic known people detection and tagging in galleries
- ✅ **Face Recognition Module**: Dedicated face detection and matching engine
- ✅ **Batch Processing**: Parallel processing scripts for syncing LinkedIn data

### Version 2.0 - Enhanced User Experience
- ✅ **Rebranded to Virsa FaceFinder** with new vibrant color scheme (Teal, Coral, Pink)
- ✅ **Dynamic Photo Counts**: Gallery counts now accurately reflect database state
- ✅ **Loading Overlays**: Visual feedback when switching gallery views or navigating pages
- ✅ **Enhanced Error Handling**: Better error messages and debugging information
- ✅ **Improved Logo**: Custom VirsaAnimation.jpeg logo in header and favicon
- ✅ **Better State Management**: Proper loading states throughout the application
- ✅ **Debug Logging**: Added console and backend logging for troubleshooting

## 👥 Known People Management

The Known People Management system allows you to build a database of frequently recognized individuals with associated LinkedIn profiles.

### Directory Structure

Store reference photos in the `storage/known_faces/` directory organized by person name:

```
storage/known_faces/
├── John Smith/
│   ├── photo1.jpg
│   ├── photo2.jpg
│   └── photo3.jpg
├── Jane Doe/
│   ├── headshot.jpg
│   └── profile.jpg
└── Bob Johnson/
    └── photo.jpg
```

### CLI Tool: scan_known_faces.py

The `scan_known_faces.py` script manages the known people database.

**Usage:**
```bash
cd backend
python scan_known_faces.py [OPTIONS]
```

**Options:**
- `--scan`: Scan the `known_faces/` directory and register new people and faces
- `--list`: Display all known people currently in the database
- `--delete <person_name>`: Delete a person and all their faces from the database
- `--reprocess-all`: Reprocess all known faces (regenerate embeddings)
- `--async`: Run scanning asynchronously using Celery workers

**Examples:**
```bash
# Scan and register new people
python scan_known_faces.py --scan

# List all known people
python scan_known_faces.py --list

# Delete a person
python scan_known_faces.py --delete "John Smith"

# Reprocess all faces (updates embeddings)
python scan_known_faces.py --reprocess-all --async
```

### LinkedIn Profile Integration

Link known people to their LinkedIn profiles for enhanced metadata and profile links in the UI.

**Adding LinkedIn Profiles:**
```bash
python add_linkedin_profiles.py
```

This interactive script prompts you to:
1. Select a known person from the database
2. Enter their LinkedIn profile URL or username
3. Add optional metadata (job title, company, etc.)

**Syncing LinkedIn Data:**
```bash
python sync_linkedin_to_matches.py
```

This script synchronizes LinkedIn profile information to all photo matches where known people have been identified. Supports parallel processing for large datasets.

**Optional: Parallel Processing**
```bash
# Use multiple processes for faster syncing
python sync_linkedin_to_matches.py --workers 4
```

### Database Collections

**known_people**
- `_id`: MongoDB ObjectId
- `name`: Person's full name
- `faces`: Array of face embeddings
- `metadata`: Dictionary with job_title, company, description, etc.
- `linkedin_profile`: LinkedIn profile URL or username
- `created_at`: Timestamp
- `updated_at`: Timestamp

**known_faces_matches**
- `_id`: MongoDB ObjectId
- `photo_id`: Reference to photo in gallery
- `person_id`: Reference to known person
- `confidence_score`: Face matching confidence (0-1)
- `bbox`: Bounding box coordinates [x, y, width, height]
- `linkedin_profile`: Denormalized LinkedIn URL for quick access
- `matched_at`: Timestamp

### UI Integration

**In Gallery View:**
- Photos with recognized known people display person avatars/labels
- Hover over person label to see name and confidence score
- Click on person name to view their LinkedIn profile (if available)

**In Photo Viewer:**
- Tagged people appear as overlays on photo faces
- LinkedIn link icon appears next to person names
- Click to open LinkedIn profile in new tab

### Auto-Tagging Workflow

Photos are automatically tagged with known people when:
1. Photo is uploaded to a gallery
2. Gallery owner clicks "Tag Known People" button
3. Face detection identifies faces in photos
4. Known person database is queried for matches
5. High-confidence matches are tagged automatically

Confidence threshold is configurable in settings.

## 📸 Photo Management Features

The gallery viewer includes built-in tools for managing and downloading photos.

### Downloading Photos

**Single Photo Download:**
1. Open photo in viewer
2. Click the download icon (top right corner)
3. Photo saves with smart filename: `{person_names}_{date}_{photo_id}.webp`

**Batch Download:**
- Photos with recognized people include metadata for batch processing
- Use frontend utilities to select and download multiple photos

**Smart Filename Generation:**
- If photo contains tagged known people: `John_Smith_Jane_Doe_2024_10_30.webp`
- If no tagged people: `gallery_photo_2024_10_30.webp`
- Format ensures easy organization and identification

### Deleting Photos

**Delete Photo (Owner Only):**
1. Only gallery owner can delete photos
2. Click delete icon in photo viewer
3. Photo and associated metadata permanently removed
4. Cannot be undone

**Permissions:**
- Gallery owner: Full delete permissions
- Shared gallery viewers: View-only (no delete)

### Photo Organization

**Photo Viewer Features:**
- Real-time loading indicators
- Quick navigation between photos
- Clear metadata display
- Tagged people with LinkedIn links
- File size and timestamp information
- Keyboard navigation support

**Gallery View Features:**
- Thumbnail previews with lazy loading
- Hover to show download/tag options
- Filter by tagged people
- Sort by date, name, or tags
- Quick search by person name

## 🛠️ How It Works

1. **User Registration**: Users create an account and upload reference photos of themselves
2. **Profile Creation**: The system extracts facial embeddings from reference photos using InsightFace
3. **Gallery Creation**: Users create galleries and upload group photos
4. **Face Detection**: Celery workers detect all faces in uploaded photos
5. **Face Recognition**: The system compares detected faces against stored embeddings in Pinecone
6. **Auto-Tagging**: Photos containing the user are automatically tagged and highlighted
7. **Photo Display**: Gallery shows all photos with smart filtering (All Photos vs My Photos)

## 📊 Database Schema

### Collections

**users**
- `_id`: MongoDB ObjectId
- `email`: User email (unique)
- `password_hash`: Hashed password
- `name`: User's full name
- `created_at`: Account creation timestamp
- `updated_at`: Last update timestamp

**user_profiles**
- `_id`: MongoDB ObjectId
- `user_id`: Reference to user
- `reference_photo_paths`: Array of stored photo paths
- `pinecone_ids`: Array of face embedding IDs in Pinecone
- `created_at`: Profile creation timestamp
- `updated_at`: Last update timestamp

**galleries**
- `_id`: MongoDB ObjectId
- `name`: Gallery name
- `description`: Gallery description
- `owner_id`: Reference to gallery owner (user)
- `share_token`: Unique shareable token (unique)
- `is_public`: Public visibility flag
- `created_at`: Gallery creation timestamp
- `updated_at`: Last update timestamp

**photos**
- `_id`: MongoDB ObjectId
- `gallery_id`: Reference to gallery
- `file_path`: Path to stored photo file
- `uploaded_at`: Upload timestamp
- `processed`: Processing completion flag
- `user_ids`: Array of user IDs detected in photo
- `tagged_people`: Array of tagged known people with confidence scores

**faces**
- `_id`: MongoDB ObjectId
- `photo_id`: Reference to photo
- `bbox`: Bounding box coordinates [x, y, width, height]
- `user_id`: Reference to user (if recognized as user's face)
- `pinecone_id`: Face embedding ID in Pinecone
- `embedding`: Face embedding vector
- `detected_at`: Detection timestamp

**known_people**
- `_id`: MongoDB ObjectId
- `name`: Person's full name
- `faces`: Array of face embeddings and metadata
- `metadata`: Dictionary with additional info (job_title, company, description)
- `linkedin_profile`: LinkedIn profile URL or username
- `created_at`: Record creation timestamp
- `updated_at`: Last update timestamp

**known_faces_matches**
- `_id`: MongoDB ObjectId
- `photo_id`: Reference to photo in gallery
- `person_id`: Reference to known person
- `confidence_score`: Face matching confidence (0-1 range)
- `bbox`: Bounding box coordinates [x, y, width, height]
- `linkedin_profile`: Denormalized LinkedIn URL for quick access
- `matched_at`: Match detection timestamp

## 🔧 Background Tasks (Celery)

The application uses Celery for asynchronous background processing of CPU-intensive face recognition tasks.

### Task Overview

**Task 1: Create User Profile** (`create_user_profile`)
- Extracts facial embeddings from reference photos
- Stores embeddings in Pinecone vector database
- Queue: `profile_creation`

**Task 2: Process Photo** (`process_photo`)
- Detects all faces in uploaded photos
- Generates face embeddings
- Stores face bounding boxes and data
- Queue: `photo_processing`

**Task 3: Recognize Faces** (`scan_all_galleries_for_user`)
- Compares detected faces against user profiles
- Creates user-photo associations
- Queue: `photo_processing`

### Celery Worker Configuration

The system is **optimized for GPU workloads** and automatically configures workers based on your platform.

#### Default Configuration (GPU-Optimized)

**Windows:**
- Pool Type: `gevent` (greenlet-based concurrency)
- Default Concurrency: **2 concurrent tasks** (optimized for GPU memory)
- Good for: Face recognition with GPU acceleration
- Prevents GPU memory overload during concurrent processing

**Linux/Mac:**
- Pool Type: `prefork` (multi-process)
- Worker Processes: **2-3 processes** with autoscaling
- Concurrency per Worker: **2 tasks**
- Total Concurrent Tasks: **4-6 tasks**
- Good for: CPU-intensive face detection + GPU acceleration

#### Why Low Concurrency?

Face recognition models load into GPU memory. High concurrency can cause:
- ❌ GPU Out-of-Memory (OOM) errors
- ❌ System crashes or freezes
- ❌ Slower processing due to GPU contention

**Recommendation:** Keep concurrency at **2** unless you have high-memory GPUs (24GB+)

### Performance Tuning

#### Adjust Concurrency for Different GPU Configurations

Set custom concurrency in `.env`:

```env
CELERY_CONCURRENCY=2  # Number of concurrent tasks
```

**GPU-Based Guidelines:**
- **4-8 GB GPU (RTX 3060, GTX 1660)**: `CELERY_CONCURRENCY=1` or `2`
- **10-12 GB GPU (RTX 3080, RTX 3060 Ti)**: `CELERY_CONCURRENCY=2` or `3`
- **16-24 GB GPU (RTX 4090, RTX 3090)**: `CELERY_CONCURRENCY=4` to `6`
- **CPU-Only (No GPU)**: `CELERY_CONCURRENCY=4` to `8` (depends on CPU cores)

**Memory Monitoring:**
```bash
# Monitor GPU memory usage (Linux/Windows with NVIDIA GPU)
nvidia-smi -l 1

# Watch for memory usage near 100% and adjust concurrency down if needed
```

#### Install gevent (Windows - Recommended)

For optimal Windows performance, install gevent:

```bash
pip install gevent greenlet
```

**Benefits:**
- 10x better task switching performance
- Lower memory overhead
- Better handling of I/O operations

Without gevent, the system automatically falls back to `solo` pool (single-threaded, slower).

### Monitoring Workers

**Check worker status:**
```bash
celery -A backend.workers.celery_app inspect active
```

**Monitor queue lengths:**
```bash
celery -A backend.workers.celery_app inspect active_queues
```

**View registered tasks:**
```bash
celery -A backend.workers.celery_app inspect registered
```

## 🔬 Face Recognition Module

The Face Recognition Module (`face-recognition-module/`) provides core face detection and matching functionality.

### Module Components

**FaceScanner** (`face_scanner.py`)
- Scans the `known_faces/` directory
- Organizes photos by person name
- Extracts and processes face embeddings
- Updates the known people database

**FaceMatcher** (`face_matcher.py`)
- Compares detected faces against known people database
- Calculates confidence scores for matches
- Returns matches with bounding box information
- Supports batch processing

**KnownPeopleDB** (`known_people_db.py`)
- Database operations for known people
- CRUD operations for person records
- Face embedding storage and retrieval
- Metadata management

### Usage in Backend

The module integrates with Celery tasks for:
- **Profile Creation**: Extract embeddings from reference photos
- **Photo Processing**: Detect faces in uploaded photos
- **Known People Tagging**: Match detected faces against known people
- **Batch Operations**: Scan and update known people database

### Performance Characteristics

- **Face Detection**: ~100-200ms per photo (CPU-dependent)
- **Face Matching**: ~10-50ms per detected face
- **Batch Scanning**: Parallelizable with multiple workers
- **Embedding Generation**: Cached for performance

### Configuration

Configure face recognition in `.env`:

```env
# Face Detection
INSIGHTFACE_MODEL=buffalo_l          # Model size: s, m, l
FACE_DETECTION_THRESHOLD=0.5          # Confidence threshold for detection
FACE_MATCH_THRESHOLD=0.6              # Confidence threshold for matching

# Performance
FACE_EMBEDDING_DIM=512                # Embedding vector dimension
BATCH_PROCESS_SIZE=32                 # Photos per batch processing
```

## 🧪 Testing

### Test Backend
```bash
cd backend
pytest
```

### Test Frontend
```bash
cd frontend
npm test
```

## 🐛 Troubleshooting

### Common Issues

**1. MongoDB Connection Error**
- Verify your `MONGODB_URI` in `.env`
- Ensure your IP is whitelisted in MongoDB Atlas
- Check network connectivity

**2. Redis Connection Error**
- Ensure Redis server is running: `redis-server`
- Check Redis is accessible: `redis-cli ping`

**3. Celery Worker Not Starting**
- Check Redis is running: `redis-cli ping`
- Verify `MONGODB_URI` is set correctly in `.env`
- On Windows: Install gevent for better performance: `pip install gevent`
- If gevent not available, worker will use `solo` pool (slower but works)

**4. Face Detection Not Working**
- Verify Pinecone API key is correct
- Check InsightFace model is downloaded
- Review Celery worker logs for errors

**5. Images Not Loading**
- Check `storage/` directory exists and has correct permissions
- Verify `STORAGE_BASE_PATH` and `STORAGE_BASE_URL` in `.env`
- Ensure FastAPI is serving static files from `/storage`

**6. Reference Photos Not Showing on Profile Page**
- Check browser console (F12 → Console tab) for `[ProfilePage]` logs
- Check backend logs for `[DEBUG] get_my_reference_photos` output
- Verify user profile exists: `db.user_profiles.findOne({"user_id": ObjectId("...")})`
- Verify reference photos exist: `db.reference_photos.find({"profile_id": ObjectId("...")})`
- Check storage files exist: Look in `storage/reference/{user_id}/`

**7. Incorrect Photo Count on My Galleries**
- The photo count is now dynamically calculated from the database
- If count is still wrong, check backend logs for `[DEBUG] Gallery ... - DB count: X`
- Verify photos exist: `db.photos.count_documents({"gallery_id": ObjectId("...")})`

**8. Loading Screen Stuck on Gallery Page**
- Check Network tab (F12 → Network) for failed API requests
- Verify pagination parameters are correct
- Check backend logs for errors during photo fetch

**9. Known People Not Recognized in Photos**
- Verify `known_faces/` directory structure is correct (person_name/photos)
- Run `python scan_known_faces.py --list` to check registered people
- Ensure reference photos are clear and well-lit
- Check face detection threshold in settings (lower = more sensitive)
- Verify Pinecone embeddings are generated: Check MongoDB `known_people` collection

**10. LinkedIn Links Not Appearing**
- Check known person has LinkedIn profile set: `python add_linkedin_profiles.py`
- Verify LinkedIn profile URL is valid
- Run `python sync_linkedin_to_matches.py` to sync profiles to matches
- Clear browser cache (F12 → Application → Clear Storage)
- Check browser console for any JSON parsing errors

**11. Photo Download Not Working**
- Verify storage directory has read permissions
- Check photo file exists in storage path
- Inspect browser console for download errors
- Verify STORAGE_BASE_PATH is correctly set

**12. scan_known_faces.py Command Not Found**
- Ensure you're in the project root directory, not `backend/`
- Run with `python scan_known_faces.py` not `scan_known_faces.py`
- On Windows, use `python` or `python.exe`
- On Mac/Linux, may need `python3`

**13. SSL Certificate Errors (CERT_HAS_EXPIRED, UNABLE_TO_VERIFY_LEAF_SIGNATURE)**
- If using self-signed certificates, your browser will show security warnings - this is expected
- Click "Advanced" and "Proceed to site" to accept the self-signed certificate
- If certificates have expired, regenerate them: `openssl req -x509 -newkey rsa:4096 -keyout certs/key.pem -out certs/cert.pem -days 365 -nodes`
- Check certificate validity: `openssl x509 -in certs/cert.pem -text -noout`

**14. CORS Errors (Access-Control-Allow-Origin)**
- Verify `CORS_ORIGINS` in `.env` matches your frontend URL
- For localhost development: `CORS_ORIGINS=https://localhost:7003`
- For custom domain: `CORS_ORIGINS=https://recommendations.vosmos.events:7003`
- Restart the backend after changing `.env`
- Check browser console for specific CORS error details

**15. Connection Refused on Port 7008 or 7003**
- Check if the ports are already in use: `netstat -ano | findstr :7008` (Windows) or `lsof -i :7008` (Linux/Mac)
- Kill the process using the port if needed
- Ensure firewall isn't blocking the ports
- Try using different ports in `.env` and `vite.config.js`

**16. GPU Out of Memory (CUDA OOM)**
- Reduce `CELERY_CONCURRENCY` in `.env` (try `CELERY_CONCURRENCY=1`)
- Monitor GPU memory: `nvidia-smi -l 1`
- Close other GPU-intensive applications
- Consider using CPU-only mode if GPU memory is insufficient
- Reduce `MAX_FACES_PER_IMAGE` in `.env`

**17. Mixed Content Errors (HTTP/HTTPS)**
- Ensure all URLs in `.env` use `https://` not `http://`
- Check `STORAGE_BASE_URL` uses HTTPS
- Verify API calls in frontend use HTTPS
- Check browser console for specific mixed content warnings

## 🔍 Debugging & Monitoring

### Frontend Debugging

**Console Logs**:
- Profile page logs are prefixed with `[ProfilePage]`
- Gallery page logs are prefixed with `[fetchPhotos]` or `[handlePageChange]`
- Open browser DevTools (F12) → Console tab to see logs in real-time

**Network Monitoring**:
- Open DevTools → Network tab to monitor API requests
- Check response status (should be 200 for success)
- View response body to see actual data returned

### Backend Debugging

**Backend Logs**:
- API endpoint logs show debug information with `[DEBUG]` prefix
- Watch for lines like `[DEBUG] get_my_reference_photos called for user_id: ...`
- Check Celery worker logs for background task processing

**MongoDB Inspection**:
```bash
# Connect to MongoDB
mongo "mongodb+srv://user:pass@cluster.mongodb.net/database"

# Check users
db.users.find({})

# Check galleries
db.galleries.find({"host_user_id": ObjectId("...")})

# Count photos in gallery
db.photos.count_documents({"gallery_id": ObjectId("...")})

# Check reference photos for user
db.reference_photos.find({"profile_id": ObjectId("...")})
```

### Performance Monitoring

**Celery Task Monitoring**:
```bash
# Check active tasks
celery -A backend.workers.celery_app inspect active

# Check queue status
celery -A backend.workers.celery_app inspect active_queues

# View task stats
celery -A backend.workers.celery_app inspect stats
```

## 🛠️ Utility Scripts

The backend includes several utility scripts for database management and data processing.

### scan_known_faces.py

Manages the known people database and face scanning operations.

```bash
# Scan known_faces directory and register people
python scan_known_faces.py --scan

# List all known people
python scan_known_faces.py --list

# Delete a person and all their faces
python scan_known_faces.py --delete "John Smith"

# Reprocess all known faces (regenerate embeddings)
python scan_known_faces.py --reprocess-all

# Async scanning with Celery workers
python scan_known_faces.py --scan --async
```

### add_linkedin_profiles.py

Interactive script to link LinkedIn profiles to known people.

```bash
# Start interactive LinkedIn profile addition
python add_linkedin_profiles.py

# Follows prompts to:
# 1. Select a known person
# 2. Enter LinkedIn URL or username
# 3. Add optional metadata
```

### sync_linkedin_to_matches.py

Synchronize LinkedIn profiles to photo matches.

```bash
# Sync LinkedIn data to all matches
python sync_linkedin_to_matches.py

# Parallel processing with custom worker count
python sync_linkedin_to_matches.py --workers 4

# Sync only recent matches
python sync_linkedin_to_matches.py --recent
```

### Other Utility Scripts

**check_database.py** - Verify database collections and count documents

**reset_database.py** - Reset database to clean state (use with caution!)

**run.py** - Unified backend startup with preflight checks

## 📝 Development Notes

### Adding New Features

1. **Backend**: Add routes in `backend/api/routes/`
2. **Frontend**: Add components/pages in `frontend/src/`
3. **Tasks**: Add Celery tasks in `backend/workers/tasks.py`
4. **Database**: Update schemas in `backend/models/database.py`
5. **Face Recognition**: Update module in `backend/face-recognition-module/`

### Code Style

- Backend: Follow PEP 8 (Python)
- Frontend: Follow Airbnb React style guide
- Use meaningful variable names
- Add docstrings to functions
- Write unit tests for new features
- Document new CLI commands and options

## 🚀 Deployment

### Production Deployment Checklist

Before deploying to production, ensure you complete these steps:

#### 1. Security Configuration

```env
# Use strong, randomly generated keys
JWT_SECRET_KEY=<generate-with-openssl-rand-base64-32>

# Use production-grade certificates (not self-signed)
# Obtain from Let's Encrypt, Cloudflare, or commercial CA
```

**Generate secure JWT secret:**
```bash
openssl rand -base64 32
```

#### 2. Database Configuration

- ✅ Use MongoDB Atlas production cluster (M10+ tier recommended)
- ✅ Enable database authentication and IP whitelisting
- ✅ Set up automated backups
- ✅ Configure replica sets for high availability

#### 3. SSL Certificates

**For Production (Let's Encrypt - Free):**
```bash
# Install Certbot
sudo apt-get install certbot  # Ubuntu/Debian

# Generate certificate
sudo certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com

# Copy certificates to project
cp /etc/letsencrypt/live/yourdomain.com/privkey.pem certs/key.pem
cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem certs/cert.pem
```

**Auto-renewal setup:**
```bash
# Add to crontab
0 0 1 * * certbot renew --quiet && cp /etc/letsencrypt/live/yourdomain.com/privkey.pem /path/to/project/certs/key.pem && cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem /path/to/project/certs/cert.pem
```

#### 4. Environment Variables

Update `.env` for production:

```env
ENVIRONMENT=production
DEBUG=false
CORS_ORIGINS=https://yourdomain.com

# Use production URLs
STORAGE_BASE_URL=https://yourdomain.com:7008/storage

# Increase security
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440  # 24 hours instead of 30 days
```

#### 5. Process Management

Use a process manager for production (not `python run.py`):

**Option 1: Systemd (Linux)**

Create `/etc/systemd/system/facefinder-backend.service`:
```ini
[Unit]
Description=Virsa FaceFinder Backend
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/Face_Recognition_Gallery_Platform
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 7008 --ssl-keyfile certs/key.pem --ssl-certfile certs/cert.pem
Restart=always

[Install]
WantedBy=multi-user.target
```

**Enable and start:**
```bash
sudo systemctl enable facefinder-backend
sudo systemctl start facefinder-backend
sudo systemctl status facefinder-backend
```

**Option 2: Docker (Cross-Platform)**

Create `Dockerfile`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
EXPOSE 7008

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "7008", "--ssl-keyfile", "certs/key.pem", "--ssl-certfile", "certs/cert.pem"]
```

**Build and run:**
```bash
docker build -t facefinder-backend .
docker run -d -p 7008:7008 --name facefinder facefinder-backend
```

#### 6. Reverse Proxy (Nginx)

Use Nginx as a reverse proxy for better performance:

```nginx
server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /path/to/certs/cert.pem;
    ssl_certificate_key /path/to/certs/key.pem;

    # Frontend
    location / {
        proxy_pass https://localhost:7003;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Backend API
    location /api {
        proxy_pass https://localhost:7008;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Storage
    location /storage {
        alias /path/to/Face_Recognition_Gallery_Platform/storage;
        expires 30d;
    }
}
```

#### 7. Performance Optimization

- ✅ Enable Redis persistence: `appendonly yes` in `redis.conf`
- ✅ Set up CDN for static assets (Cloudflare, AWS CloudFront)
- ✅ Configure database connection pooling
- ✅ Enable gzip compression in Nginx
- ✅ Set up monitoring (Prometheus, Grafana, or Datadog)

#### 8. Monitoring & Logging

**Application Monitoring:**
```bash
# Install Prometheus client
pip install prometheus-client

# Monitor Celery
celery -A backend.workers.celery_app inspect stats
```

**Log Management:**
```bash
# Configure log rotation in /etc/logrotate.d/facefinder
/var/log/facefinder/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
}
```

#### 9. Backup Strategy

- ✅ Automated MongoDB backups (daily)
- ✅ Storage directory backups (S3, Google Cloud Storage)
- ✅ Configuration backup (`.env`, certificates)
- ✅ Test restore procedures regularly

#### 10. Scaling Considerations

**Horizontal Scaling:**
- Use load balancer (Nginx, HAProxy, AWS ALB)
- Multiple Celery workers across different machines
- Shared storage (NFS, S3, Azure Blob)
- Redis Cluster for high availability

**Vertical Scaling:**
- Increase Celery concurrency with more GPU memory
- Use dedicated GPU servers for face recognition
- Separate database and application servers

## 🗑️ Cleanup

To remove obsolete files from development:

```bash
python cleanup.py
```

This will safely remove:
- Old PostgreSQL/SQLAlchemy scripts
- Duplicate configuration files
- Python cache files
- Planning documents

## ❓ Frequently Asked Questions (FAQ)

### General Questions

**Q: Can I use this without a GPU?**
A: Yes! The application works with CPU-only mode, though face recognition will be slower. Simply install PyTorch without CUDA support.

**Q: How much does it cost to run?**
A: Main costs are MongoDB Atlas (~$0-57/month depending on tier) and Pinecone (~$70/month for 1 pod). Redis and the application are free/open-source.

**Q: Can I use local storage instead of Pinecone?**
A: Currently, Pinecone is required for vector similarity search. We may add support for local alternatives like FAISS or ChromaDB in the future.

**Q: How many photos can the system handle?**
A: Tested with galleries of 1000+ photos. Performance depends on your hardware (GPU, RAM, storage).

**Q: Can I deploy this to the cloud?**
A: Yes! It works on AWS, Azure, Google Cloud, DigitalOcean, or any VPS with Docker support.

### Technical Questions

**Q: Why do I need HTTPS in development?**
A: Modern browsers require HTTPS for many features like secure cookies, service workers, and better CORS handling. Self-signed certificates work fine for development.

**Q: Can I change the ports (7008, 7003)?**
A: Yes. Update the ports in `run.py`, `vite.config.js`, and `.env` (CORS_ORIGINS, STORAGE_BASE_URL).

**Q: How accurate is the face recognition?**
A: InsightFace achieves 99%+ accuracy on standard benchmarks. Accuracy depends on photo quality, lighting, and face angle.

**Q: Can it recognize people with masks?**
A: Partially. Face recognition accuracy drops significantly with masks. It works best with full, unobstructed faces.

**Q: How do I add more face recognition models?**
A: Edit `INSIGHTFACE_MODEL` in `.env`. Options: `buffalo_s` (small), `buffalo_m` (medium), `buffalo_l` (large).

**Q: Can multiple users upload to the same gallery?**
A: Currently, only the gallery owner can upload photos. Shared users have view-only access.

**Q: How do I reset the database?**
A: Use `python reset_database.py` (if available) or manually delete collections in MongoDB Atlas. **Warning:** This deletes all data!

### Privacy & Security

**Q: Where are photos stored?**
A: Photos are stored locally in the `storage/` directory on your server. They are not uploaded to third parties (except face embeddings to Pinecone).

**Q: What data is sent to Pinecone?**
A: Only numerical face embeddings (512-dimensional vectors) are sent to Pinecone. No actual photos are uploaded.

**Q: Is this GDPR compliant?**
A: The application provides tools for data deletion and user privacy, but you must configure it properly and add necessary consent flows for GDPR compliance.

**Q: Can I use this commercially?**
A: Check the licenses of dependencies (InsightFace, Pinecone) and add your own license to this project before commercial use.

## 🤝 Contributing

We welcome contributions! Here's how you can help:

### Ways to Contribute

1. **Report Bugs**: Open an issue with detailed reproduction steps
2. **Suggest Features**: Open an issue describing the feature and use case
3. **Improve Documentation**: Fix typos, add examples, clarify instructions
4. **Submit Code**: Fork the repo, create a feature branch, and submit a PR

### Development Workflow

```bash
# Fork and clone the repository
git clone https://github.com/yourusername/Face_Recognition_Gallery_Platform.git
cd Face_Recognition_Gallery_Platform

# Create a feature branch
git checkout -b feature/your-feature-name

# Make changes and test thoroughly
# ...

# Commit with clear messages
git commit -m "Add feature: your feature description"

# Push and create a Pull Request
git push origin feature/your-feature-name
```

### Code Guidelines

- Follow PEP 8 for Python code
- Use ESLint for JavaScript/React code
- Write clear commit messages
- Add docstrings to new functions
- Include unit tests for new features
- Update documentation for API changes

### Testing

```bash
# Backend tests
pytest backend/tests/

# Frontend tests
cd frontend && npm test

# Linting
flake8 backend/
cd frontend && npm run lint
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

**Note:** This project uses several third-party libraries with their own licenses:
- **InsightFace**: MIT License
- **FastAPI**: MIT License
- **React**: MIT License
- **Pinecone**: Commercial service (separate terms)
- **MongoDB Atlas**: Commercial service (separate terms)

## 👥 Contributors

- **Main Developer**: [Your Name/Organization]
- **Contributors**: See [CONTRIBUTORS.md](CONTRIBUTORS.md) for a full list

Want to see your name here? Check out our [Contributing](#-contributing) section!

## 🙏 Acknowledgments

This project wouldn't be possible without these amazing open-source projects and services:

- **[InsightFace](https://github.com/deepinsight/insightface)**: State-of-the-art face recognition models
- **[Pinecone](https://www.pinecone.io/)**: Vector database for fast similarity search
- **[FastAPI](https://fastapi.tiangolo.com/)**: Modern, fast Python web framework
- **[React](https://react.dev/)**: Frontend JavaScript library
- **[Celery](https://docs.celeryproject.org/)**: Distributed task queue
- **[Redis](https://redis.io/)**: In-memory data store
- **[MongoDB](https://www.mongodb.com/)**: NoSQL database
- **[Vite](https://vitejs.dev/)**: Lightning-fast frontend build tool
- **[Tailwind CSS](https://tailwindcss.com/)**: Utility-first CSS framework
- **[PyTorch](https://pytorch.org/)**: Machine learning framework
- **[Uvicorn](https://www.uvicorn.org/)**: ASGI web server

Special thanks to the open-source community for making projects like this possible!

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/Face_Recognition_Gallery_Platform/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/Face_Recognition_Gallery_Platform/discussions)
- **Email**: your-email@example.com

---

**Made with ❤️ by [Your Name/Organization]**
