"""
FastAPI webhook server entrypoint for Monsterrr.
"""

from fastapi import FastAPI
import logging

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Monsterrr AI is running."}

# TODO: Add webhook endpoints and agent integration

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
