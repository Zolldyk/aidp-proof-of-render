# AIDP Proof of Render

[![CI/CD Pipeline](https://github.com/Zolldyk/aidp-proof-of-render/workflows/CI%2FCD%20Pipeline/badge.svg)](https://github.com/Zolldyk/aidp-proof-of-render/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A decentralized GPU rendering service with cryptographic proof of work, built for the AIDP network.

## Project Status

### Epic 1: Foundation & Core Rendering Pipeline ✅ COMPLETE
- [x] Story 1.1: Project Repository Setup
- [x] Story 1.2: AIDP Integration Research
- [x] Story 1.3: Blender Headless Rendering POC
- [x] Story 1.4: Scene Preset System
- [x] Story 1.5: File Upload Endpoint
- [x] Story 1.6: Render Job Submission (Local Fallback)
- [x] Story 1.7: Pipeline Integration & Testing

### Epic 2: Proof Generation & Verification (Planned)
### Epic 3: Frontend Implementation (Planned)
### Epic 4: Gallery & Polish (Planned)

## About

AIDP Proof of Render enables users to upload 3D models (GLTF format), render them using cloud GPU infrastructure via the AIDP (AI Decentralized Processing) network, and receive cryptographic proof that the rendering was completed. The system provides:

- **Anonymous Upload**: Zero-friction file upload without authentication
- **Decentralized GPU Rendering**: Leverages AIDP network for distributed rendering tasks
- **Cryptographic Proof**: SHA-256 proof of work for render verification
- **Time-Limited Storage**: 24-hour automatic file cleanup
- **Gallery View**: Public gallery of rendered outputs

## Tech Stack

This project uses a modern full-stack architecture optimized for rapid development:

**Frontend:**
- React 19.2.3 with TypeScript 5.9.3
- Vite 7.3.0 for lightning-fast development
- Tailwind CSS 4.1.18 with Lightning CSS engine
- React Router for client-side routing

**Backend:**
- Python 3.13+ with FastAPI 0.128.0
- Blender 3.6 LTS for headless rendering
- Uvicorn ASGI server
- Pydantic for data validation

**Infrastructure:**
- Docker for containerization
- Railway (backend deployment)
- Vercel (frontend deployment)
- GitHub Actions for CI/CD

## Quick Start

Get the project running in under 5 minutes:

### Prerequisites

- Node.js 20+
- Python 3.13+
- Docker (optional, for containerized backend)

### Frontend Setup

```bash
# Clone the repository
git clone https://github.com/Zolldyk/aidp-proof-of-render.git
cd aidp-proof-of-render

# Install frontend dependencies
cd frontend
npm install

# Start development server
npm run dev
```

The frontend will be available at `http://localhost:5173`

### Backend Setup

```bash
# From project root, navigate to backend
cd backend

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the API server
uvicorn app.main:app --reload
```

The backend will be available at `http://localhost:8000`
- API documentation: `http://localhost:8000/docs`
- Alternative docs: `http://localhost:8000/redoc`

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/upload` | POST | Upload .gltf asset (max 10MB) |
| `/api/render` | POST | Submit render job with preset |
| `/api/status/{job_id}` | GET | Check job status |
| `/api/download/{job_id}` | GET | Download rendered PNG |
| `/api/presets` | GET | List available presets |
| `/health` | GET | Health check |

### Example curl Commands

```bash
# 1. Upload a .gltf asset
curl -X POST http://localhost:8000/api/upload \
  -F "file=@model.gltf"

# 2. Submit render job (use jobId from step 1)
curl -X POST http://localhost:8000/api/render \
  -H "Content-Type: application/json" \
  -d '{"jobId": "YOUR_JOB_ID", "preset": "studio"}'

# 3. Poll status until complete
curl http://localhost:8000/api/status/YOUR_JOB_ID

# 4. Download rendered image
curl -o render.png http://localhost:8000/api/download/YOUR_JOB_ID

# Available presets: studio, sunset, dramatic
```

### Docker Setup (Alternative)

```bash
# Build and run with Docker Compose
cd backend
docker-compose up --build
```

## Project Structure

```
aidp-proof-of-render/
├── frontend/           # React + TypeScript frontend
├── backend/            # FastAPI backend with Blender
├── test-assets/        # Sample GLTF files for testing
├── scripts/            # Utility scripts
└── .github/workflows/  # CI/CD configuration
```

## Architecture

```
[User] → [React Frontend] → [FastAPI Backend] → [AIDP Network]
                                    ↓
                            [Blender Renderer]
                                    ↓
                            [Proof Generator]
```


## Development Workflow

1. **Frontend**: `npm run dev` (auto-reloads on changes)
2. **Backend**: `uvicorn app.main:app --reload` (auto-reloads on changes)
3. **Linting**:
   - Frontend: `npm run lint`
   - Backend: `black .` and `isort .`
4. **Testing**:
   - Frontend: `npm run test`
   - Backend: `pytest`

## Contributing

We welcome contributions! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes with clear messages
4. Run linting and tests before pushing
5. Submit a pull request

