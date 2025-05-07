# Ascertain: Medical Document Analysis API

A FastAPI-based backend service for medical document analysis that extracts structured information from clinical notes and provides FHIR conversion capabilities.

## Quick Setup

```bash
# Initial setup (one-time):
make setup

# Edit .env file to add your API keys
# Especially OPENAI_API_KEY is required

# Run the tests with Docker:
make test

# Start the application with Docker:
make up
```

The API will be available at `http://localhost:8000`

## Requirements

- Docker and Docker Compose
- Python 3.10+
- OpenAI API key

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check endpoint |
| `/documents/` | GET | Get all documents |
| `/documents/` | POST | Create a new document |
| `/documents/{document_id}` | GET | Get a specific document |
| `/analyze-note` | POST | Analyze a clinical note and extract structured information |
| `/extract-structured` | POST | Extract structured information from a clinical note |
| `/to_fhir` | POST | Convert clinical note data to FHIR format |

## Available Commands

| Command | Description |
|---------|-------------|
| `make setup` | Set up the development environment (first time setup) |
| `make env` | Set up environment variables from development template |
| `make up` | Start the application in Docker with hot-reloading |
| `make build` | Build and start the application in Docker with hot-reloading |
| `make upf` | Start the application in Docker foreground with logs |
| `make down` | Stop Docker services |
| `make logs` | View Docker logs |
| `make test` | Run tests locally (starts PostgreSQL in Docker) |
| `make test-docker` | Run tests in Docker |
| `make test-cleanup` | Stop PostgreSQL container after tests |
| `make prod` | Start the application in production mode |
| `make prod-logs` | View production logs |

## Docker Deployment

The application includes a `docker-compose.yml` for local development and a `docker-compose.prod.yml` for production deployment.

### Local Development

```bash
# Start the application in development mode
make up

# View logs
make logs
```
## Example API Request

```bash
# Analyze a clinical note
curl -X POST http://localhost:8000/analyze-note \
  -H "Content-Type: application/json" \
  -d '{"note_text": "Patient presents with fever of 101.2F for 3 days. Dr. Smith recommends rest and fluids."}'
```