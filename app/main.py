from fastapi import FastAPI

app = FastAPI(title="se480-brittonpeterson-service")


@app.get("/")
def hello():
    return {"message": "Hello from Britton Peterson's SE 480 service"}


@app.get("/health")
def health():
    return {"status": "ok"}
