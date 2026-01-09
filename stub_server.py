import os
import asyncio
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Union

app = FastAPI()

DELAY_MS = int(os.getenv("DELAY_MS", "1000"))

class SingleRequest(BaseModel):
    model: str
    input: str

class BatchRequest(BaseModel):
    model: str
    inputs: List[str]

class SingleResponse(BaseModel):
    output: str

class BatchResponse(BaseModel):
    outputs: List[str]

@app.post("/api")
async def api_endpoint(request: Union[SingleRequest, BatchRequest]):
    if hasattr(request, 'input'):
        # Single request
        delay = DELAY_MS / 1000.0
        await asyncio.sleep(delay)
        return SingleResponse(output=f"Response for: {request.input}")
    elif hasattr(request, 'inputs'):
        # Batch request
        num_inputs = len(request.inputs)
        delay = (DELAY_MS / num_inputs) / 1000.0  # Faster processing for batches
        await asyncio.sleep(delay)
        outputs = [f"Response for: {inp}" for inp in request.inputs]
        return BatchResponse(outputs=outputs)
    else:
        return {"error": "Invalid request format"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)