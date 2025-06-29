# Fingyan Financial Platform 📈

Fingyan is a scalable, AI-powered financial web platform designed for Indian retail and institutional investors. It provides real-time Indian stock market insights, predictive analytics, and portfolio management tools. The platform is built with a modular architecture using Streamlit for the frontend and FastAPI for the backend, containerized with Docker, and designed for Kubernetes orchestration.

## Table of Contents
- [Features](#features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Folder Structure](#folder-structure)
- [Local Development Setup](#local-development-setup)
  - [Prerequisites](#prerequisites)
  - [Environment Variables](#environment-variables)
  - [Running with Docker Compose](#running-with-docker-compose)
- [Running Tests](#running-tests)
- [API Documentation](#api-documentation)
- [CI/CD Pipeline](#cicd-pipeline)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Contributing](#contributing)

## Features
*   **Real-time Market Data:** Access live stock prices, index values, forex rates, and commodity prices.
*   **Interactive Technical Charts:** Candlestick charts with common technical indicators (MA, RSI, MACD).
*   **Portfolio Management:** Create and manage multiple investment portfolios, track holdings.
*   **Alerts System:** Set up price-based alerts for specific stocks.
*   **AI-Powered Predictions:** Get short-term trend predictions for stocks (experimental, using Prophet).
*   **Market News:** View news articles related to specific symbols or general market trends.
*   **Modular UI:** Responsive frontend built with Streamlit.
*   **Scalable Backend:** Robust FastAPI microservices for data delivery and operations.

## Architecture
The platform follows a microservices-oriented architecture:
*   **Frontend:** A Streamlit application providing the user interface.
*   **Backend:** FastAPI application serving various API endpoints for market data, portfolio management, alerts, predictions, and news.
*   **Database:** PostgreSQL for persistent storage (portfolios, users, alerts).
*   **Cache:** Redis for caching frequently accessed market data and news.
*   **AI/ML Service:** (Currently integrated within backend) Prophet model for trend predictions. Future models can be separate services.
*   **Containerization:** Docker for packaging applications.
*   **Orchestration:** Kubernetes manifests provided for deployment.

For a visual representation, see the [architecture_diagram.mmd](architecture_diagram.mmd) (Mermaid syntax).

## Tech Stack
*   **Frontend:** Streamlit, Plotly
*   **Backend:** Python, FastAPI, SQLAlchemy, Pydantic, Uvicorn
*   **Data Sources (Primary):** `yfinance` (for market data, news)
*   **AI Layer:** Facebook Prophet (for trend prediction)
*   **Database:** PostgreSQL
*   **Cache:** Redis
*   **Infrastructure & CI/CD:** Docker, Kubernetes, GitHub Actions
*   **Testing:** Pytest, `fastapi.testclient`
*   **Monitoring:** Sentry (integration included)

## Folder Structure
```
fingyan_financial_platform/
├── .github/workflows/        # GitHub Actions CI/CD pipeline
├── backend/                  # FastAPI backend application
│   ├── alembic/              # Alembic database migrations
│   ├── api/                  # API routers (endpoints)
│   ├── models/               # Pydantic and SQLAlchemy models
│   ├── services/             # Business logic and external service interactions
│   ├── tests/                # Backend unit/integration tests
│   ├── Dockerfile
│   └── main.py               # FastAPI app entry point
├── frontend/                 # Streamlit frontend application
│   ├── assets/               # Static assets (images, css - if any)
│   ├── components/           # Reusable Streamlit components (future)
│   ├── pages/                # Individual Streamlit pages
│   ├── utils/                # Utility functions (e.g., api_client.py)
│   ├── Dockerfile
│   └── app.py                # Main Streamlit app entry point
├── k8s/                      # Kubernetes manifests
│   ├── config/
│   ├── deployments/
│   ├── ingress/
│   ├── secrets/
│   └── services/
├── docker-compose.yml        # Docker Compose for local development
├── requirements.txt          # Python dependencies for both backend & frontend
├── architecture_diagram.mmd  # System architecture diagram
└── README.md                 # This file
```

## Local Development Setup

### Prerequisites
*   Docker and Docker Compose installed.
*   Git for cloning the repository.
*   A `.env` file in the project root (optional, for overriding default credentials).

### Environment Variables
The `docker-compose.yml` file defines default environment variables. You can override some of these by creating a `.env` file in the `fingyan_financial_platform` project root directory. For example:
```env
# .env (optional - defaults are in docker-compose.yml)
POSTGRES_USER=myuser
POSTGRES_PASSWORD=mypassword
POSTGRES_DB=fingyan_local_db

# SENTRY_DSN=your_sentry_dsn_here # For backend error tracking
# SENTRY_ENVIRONMENT=development
```
If this file is present, Docker Compose will automatically use these values.

### Running with Docker Compose
1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd fingyan_financial_platform
    ```
2.  **Build and run the services:**
    ```bash
    docker-compose up --build
    ```
    This will build the Docker images for the backend and frontend, and start all services (backend, frontend, postgres_db, redis_cache).
    *   The **Frontend (Streamlit)** will be accessible at `http://localhost:8501`.
    *   The **Backend (FastAPI)** will be accessible at `http://localhost:8000`. API docs at `http://localhost:8000/docs`.
    *   PostgreSQL will be exposed on `localhost:5432` (for direct DB tools, if needed).
    *   Redis will be exposed on `localhost:6379`.

3.  **Database Migrations (First time or after model changes):**
    For initial development, the backend application's startup event (in `backend/main.py`) calls `create_database_tables()`. This uses SQLAlchemy's `Base.metadata.create_all(bind=engine)` to create any missing tables based on current models. This is convenient for getting started quickly.

    For robust schema versioning and managing changes over time (migrations), Alembic is configured:
    *   Ensure the database container (`postgres_db`) is running via `docker-compose up`.
    *   Execute Alembic commands inside the backend container or ensure your local environment can connect to the Dockerized DB (by setting `POSTGRES_HOST_ALEMBIC=localhost` and other `POSTGRES_*` env vars if running `alembic` locally).
    *   To apply migrations using the running backend container:
        ```bash
        docker-compose exec backend alembic upgrade head
        ```
    *   To generate a new migration (after changing `db_models.py`):
        ```bash
        # Ensure DB is accessible for autogenerate, or create empty and fill manually
        docker-compose exec backend alembic revision -m "your_migration_message" --autogenerate
        # Then apply:
        docker-compose exec backend alembic upgrade head
        ```
        (Note: Autogenerate from within Docker might need `DATABASE_URL` fully set, or component vars correctly pointing to `postgres_db` service name). The current `env.py` for Alembic prioritizes component vars.

4.  **Stopping the services:**
    Press `Ctrl+C` in the terminal where `docker-compose up` is running, then:
    ```bash
    docker-compose down
    ```
    To remove volumes (like PostgreSQL data): `docker-compose down -v`

## Running Tests
Unit tests for the backend are located in `backend/tests/`.
1.  Ensure development dependencies are installed (if running locally outside Docker, including `pytest`, `httpx`).
2.  From the project root (`fingyan_financial_platform/`):
    ```bash
    # Ensure PYTHONPATH is set if needed for imports to work, e.g.:
    # export PYTHONPATH=.
    pytest backend/tests --cov=backend
    ```
    The CI pipeline also runs these tests automatically.

## API Documentation
The FastAPI backend provides automatic interactive API documentation:
*   **Swagger UI:** Accessible at `http://localhost:8000/docs` when running locally.
*   **ReDoc:** Accessible at `http://localhost:8000/redoc`.

## CI/CD Pipeline
The project uses GitHub Actions for CI/CD, defined in `.github/workflows/ci-cd.yml`. The pipeline includes:
*   Linting (Ruff, Black) and type checking (MyPy).
*   Unit tests with Pytest and code coverage.
*   Building Docker images for frontend and backend.
*   Pushing images to GitHub Container Registry (GHCR) on pushes to `main` or `develop`.
*   (Placeholder) Deployment steps for Kubernetes.

## Kubernetes Deployment
Kubernetes manifests are provided in the `k8s/` directory for deploying the application stack (PostgreSQL, Redis, Backend, Frontend, Ingress).
*   `k8s/config/`: ConfigMaps.
*   `k8s/secrets/`: Secret definitions (use placeholder base64 values; replace with real ones).
*   `k8s/deployments/`: Deployments for frontend/backend, StatefulSet for PostgreSQL, Deployment for Redis.
*   `k8s/services/`: Kubernetes Services for each component.
*   `k8s/ingress/`: Ingress resource definition.

**Deployment Steps (High-Level):**
1.  Ensure you have a Kubernetes cluster and `kubectl` configured.
2.  Ensure an Ingress controller (e.g., NGINX Ingress) is installed in your cluster.
3.  (Optional) Create a dedicated namespace: `kubectl apply -f k8s/config/app-configmap.yaml` (if namespace definition is included there or create separately: `kubectl create namespace fingyan-ns`).
4.  **Important:** Update placeholder image names in deployment YAMLs (e.g., `YOUR_DOCKER_REGISTRY/fingyan-backend:latest`) to point to your actual images pushed to a container registry (like GHCR after the CI pipeline runs).
5.  **Important:** Update secret values in `k8s/secrets/postgres-secret.yaml` with actual base64 encoded credentials.
6.  Apply the manifests (order can matter for dependencies, but K8s generally handles it):
    ```bash
    kubectl apply -n fingyan-ns -f k8s/config/
    kubectl apply -n fingyan-ns -f k8s/secrets/
    # Apply PersistentVolumeClaims if not part of deployment files (Redis PVC is in its deployment yaml)
    kubectl apply -n fingyan-ns -f k8s/deployments/postgres-statefulset.yaml # Includes PVC template
    kubectl apply -n fingyan-ns -f k8s/services/postgres-service.yaml
    kubectl apply -n fingyan-ns -f k8s/deployments/redis-deployment.yaml # Includes PVC
    kubectl apply -n fingyan-ns -f k8s/services/redis-service.yaml
    kubectl apply -n fingyan-ns -f k8s/deployments/backend-deployment.yaml
    kubectl apply -n fingyan-ns -f k8s/services/backend-service.yaml
    kubectl apply -n fingyan-ns -f k8s/deployments/frontend-deployment.yaml
    kubectl apply -n fingyan-ns -f k8s/services/frontend-service.yaml
    # Update your-fingyan-app.com in ingress.yaml before applying
    kubectl apply -n fingyan-ns -f k8s/ingress/app-ingress.yaml
    ```
7.  Access the application via the Ingress host/IP.

## Contributing
(Placeholder for contribution guidelines if this were an open project).

---
*This README provides a snapshot of the project setup and guidance. Details may evolve.*
