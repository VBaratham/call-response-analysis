# Call/Response Analysis Web App

A unified web application for analyzing call and response patterns in audio recordings. This app combines vocal separation, automatic section detection, pitch analysis, and manual refinement tools into a single interface.

## Features

- **Audio Upload**: Upload audio files (WAV, MP3, FLAC, OGG, M4A)
- **Vocal Separation**: Automatic vocal extraction using Demucs
- **Section Detection**: Automatic detection of call/response sections using pitch-based fingerprinting
- **Waveform Editor**: Interactive waveform visualization with section editing
  - Drag to resize section boundaries
  - Click to select sections
  - Keyboard shortcuts for quick editing
- **Pitch Alignment**: Compare pitch contours between call/response pairs
  - Adjust time offset with live correlation updates
  - Visual pitch contour comparison
- **Project Export/Import**: Save and resume your work

## Quick Start

### Development Mode

1. **Start the backend:**
   ```bash
   cd backend
   pip install -r requirements.txt
   uvicorn main:app --reload --port 8000
   ```

2. **Start the frontend:**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

3. Open http://localhost:5173 in your browser

### Using Docker

**Production build:**
```bash
docker-compose up --build
```

**Development with hot reload:**
```bash
docker-compose --profile dev up --build dev
```

## Architecture

```
call_response_app/
├── backend/                 # FastAPI backend
│   ├── api/                 # API route handlers
│   │   ├── upload.py        # File upload endpoints
│   │   ├── processing.py    # Audio processing endpoints
│   │   ├── sections.py      # Section CRUD endpoints
│   │   ├── alignment.py     # Pitch alignment endpoints
│   │   └── export.py        # Project export/import
│   ├── services/            # Business logic
│   │   ├── audio_processor.py   # Demucs vocal separation
│   │   ├── fingerprinter.py     # Call/response detection
│   │   └── pitch_estimator.py   # Pitch contour extraction
│   ├── models/              # Pydantic schemas
│   └── main.py              # FastAPI app entry point
├── frontend/                # Vue.js frontend
│   ├── src/
│   │   ├── components/      # Vue components
│   │   ├── stores/          # Pinia state management
│   │   └── services/        # API client
│   └── package.json
├── data/                    # Session data storage
├── Dockerfile               # Production Docker image
├── Dockerfile.dev           # Development Docker image
└── docker-compose.yml       # Docker orchestration
```

## API Endpoints

### Upload & Sessions
- `POST /api/upload` - Upload audio file
- `GET /api/sessions` - List all sessions
- `GET /api/sessions/{id}/metadata` - Get session metadata
- `DELETE /api/sessions/{id}` - Delete session

### Processing
- `POST /api/sessions/{id}/process` - Run full processing pipeline
- `POST /api/sessions/{id}/separate-vocals` - Separate vocals only
- `POST /api/sessions/{id}/detect-sections` - Detect sections only
- `POST /api/sessions/{id}/estimate-pitch` - Estimate pitch only
- `GET /api/sessions/{id}/status` - Get processing status

### Sections
- `GET /api/sessions/{id}/sections` - Get all sections
- `POST /api/sessions/{id}/sections` - Create section
- `PUT /api/sessions/{id}/sections/{section_id}` - Update section
- `DELETE /api/sessions/{id}/sections/{section_id}` - Delete section
- `POST /api/sessions/{id}/sections/{section_id}/toggle-label` - Toggle call/response
- `POST /api/sessions/{id}/sections/{section_id}/split` - Split section
- `POST /api/sessions/{id}/sections/merge` - Merge sections

### Alignment
- `GET /api/sessions/{id}/pairs` - Get call/response pairs
- `GET /api/sessions/{id}/pairs/{pair_id}/pitch` - Get pitch data for pair
- `GET /api/sessions/{id}/pairs/{pair_id}/metrics` - Calculate correlation metrics
- `PUT /api/sessions/{id}/alignments/{pair_id}` - Update alignment offset

### Export/Import
- `GET /api/sessions/{id}/export` - Export full project
- `POST /api/sessions/{id}/import` - Import project data

## Keyboard Shortcuts

### Waveform Editor
- `Space` - Play/Pause
- `T` - Toggle section label (call ↔ response)
- `Delete` - Delete selected section
- `S` - Split section at playhead
- `Cmd+Z` - Undo
- `Cmd+Shift+Z` - Redo

### Pitch Alignment
- `←` / `→` - Previous/Next pair

## AWS Deployment

The app is designed for easy AWS deployment:

1. **ECS/Fargate**: Use the provided Dockerfile
2. **S3**: Store uploaded audio files
3. **RDS/DynamoDB**: Store session metadata (optional)
4. **CloudFront**: CDN for frontend assets

Example ECS task definition environment variables:
```json
{
  "DATA_DIR": "/app/data",
  "AWS_S3_BUCKET": "your-bucket-name"
}
```

## Technology Stack

- **Backend**: FastAPI, Python 3.11
- **Frontend**: Vue 3, Pinia, Chart.js, wavesurfer.js
- **Audio Processing**: Demucs, librosa, soundfile
- **Containerization**: Docker, docker-compose

## License

MIT
