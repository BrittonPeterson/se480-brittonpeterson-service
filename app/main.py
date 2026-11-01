from fastapi import FastAPI

app = FastAPI(title="SE 480 hello service")


@app.get("/")
def hello():
    return {"message": "Hello from SE 480"}


@app.get("/health")
def health():
    return {"status": "ok"}
