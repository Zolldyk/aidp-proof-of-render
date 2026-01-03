# AIDP Proof of Render

[![CI/CD Pipeline](https://github.com/Zolldyk/aidp-proof-of-render/workflows/CI%2FCD%20Pipeline/badge.svg)](https://github.com/Zolldyk/aidp-proof-of-render/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A decentralized GPU rendering service with cryptographic proof of work, built for the AIDP network.

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

For complete tech stack details, see [`docs/architecture/tech-stack.md`](docs/architecture/tech-stack.md).

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
├── docs/               # Project documentation
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

_Detailed architecture diagram coming soon_

## Documentation

- **Product Requirements**: [`docs/prd.md`](docs/prd.md)
- **Architecture**: [`docs/architecture/`](docs/architecture/)
- **API Specification**: [`docs/architecture/api-specification.md`](docs/architecture/api-specification.md)
- **User Stories**: [`docs/stories/`](docs/stories/)

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

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contact

For questions or support, please open an issue on GitHub.

---

Built with ❤️ for the AIDP GPU Rendering Competition
