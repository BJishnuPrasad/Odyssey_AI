import json
import os
import subprocess
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import threading

app = FastAPI(title="Odyssey AI Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

REPORT_PATH = "outputs/reports/eval_report.json"
pipeline_thread = None

class QueryRequest(BaseModel):
    query: str

def run_pipeline_bg():
    subprocess.run([".venv/Scripts/python", "pipeline.py"])

@app.post("/api/query")
def submit_query(request: QueryRequest):
    global pipeline_thread
    q = request.query.lower()
    
    # Simple Mock AI Logic
    if "run" in q or "train" in q or "pipeline" in q or "start" in q:
        if pipeline_thread and pipeline_thread.is_alive():
            return {"status": "success", "message": "Pipeline is already running in the background! Please wait."}
        
        pipeline_thread = threading.Thread(target=run_pipeline_bg)
        pipeline_thread.start()
        return {"status": "success", "message": "🚀 Understood! I have launched the Odyssey ML Pipeline in the background. Generating GeoTIFFs and Reports now..."}
    
    elif "report" in q or "accuracy" in q or "result" in q or "model" in q:
        if not os.path.exists(REPORT_PATH):
            return {"status": "success", "message": "The model report isn't generated yet. Try asking me to 'run the pipeline' first."}
        with open(REPORT_PATH, "r") as f:
            data = json.load(f)
            auc = data.get('auc_roc', 'N/A')
            return {"status": "success", "message": f"📊 The Random Forest model achieved an AUC-ROC score of {auc:.4f}."}
    
    elif "hello" in q or "hi" in q:
        return {"status": "success", "message": "Hello! I am Odyssey AI. You can ask me to 'run the pipeline' or 'show model accuracy'."}
    
    else:
        return {
            "status": "success", 
            "message": f"I received your query: '{request.query}'. I am a geospatial AI assistant. Ask me to 'run the pipeline' or 'check model accuracy' to interact with the backend!"
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
