from fastapi import FastAPI

app = FastAPI(
    title="Crokuta Research Agent",
    description="Autonomous research and intelligence API",
    version="0.1.0"
)

@app.get("/")
def root():
    return {
        "name": "Crokuta Research Agent",
        "status": "running"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}