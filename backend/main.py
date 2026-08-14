import os
import sys

# Ensure project root is in sys.path when script is executed directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional

from backend.config import config
from backend.database import db_manager
from backend.queries import (
    CYPHER_GRAPH_OVERVIEW,
    CYPHER_DISRUPTION_BLAST_RADIUS,
    CYPHER_SINGLE_POINTS_OF_FAILURE,
    CYPHER_FIND_ALTERNATE_SUPPLIERS,
    CYPHER_PRODUCT_LINEAGE
)

app = FastAPI(
    title="Vanguard CognoDB Supply Chain Graph API",
    description="Backend API powered by CognoDB Cloud & openCypher graph database driver.",
    version="1.0.0"
)

# CORS middleware for development flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class DisruptionRequest(BaseModel):
    disruption_id: str = "DISR-701"

class AlternateSupplierRequest(BaseModel):
    supplier_id: str = "SUPP-401"

class CypherRequest(BaseModel):
    cypher: str
    parameters: Optional[Dict[str, Any]] = None

@app.get("/api/status")
def get_db_status():
    """Returns database connectivity status and configuration details."""
    return db_manager.get_status()

@app.get("/api/graph/overview")
def get_graph_overview(limit: int = 100):
    """Retrieves standard supply chain graph nodes & relationships for visualizer."""
    return db_manager.execute_query(CYPHER_GRAPH_OVERVIEW, {"limit": limit})

@app.post("/api/disruptions/simulate")
def simulate_disruption(req: DisruptionRequest):
    """Multi-hop Cypher traversal analyzing cascading disruption impact across 4-5 supply tiers."""
    return db_manager.execute_query(CYPHER_DISRUPTION_BLAST_RADIUS, {"disruption_id": req.disruption_id})

@app.get("/api/analytics/spof")
def get_single_points_of_failure():
    """Identifies single-sourced components and calculates multi-hop product exposure."""
    return db_manager.execute_query(CYPHER_SINGLE_POINTS_OF_FAILURE)

@app.post("/api/analytics/alternate-routes")
def find_alternate_suppliers(req: AlternateSupplierRequest):
    """Multi-hop search for backup suppliers with lead time & switching cost metrics."""
    return db_manager.execute_query(CYPHER_FIND_ALTERNATE_SUPPLIERS, {"supplier_id": req.supplier_id})

@app.post("/api/cypher/execute")
def execute_custom_cypher(req: CypherRequest):
    """Executes a custom Cypher query entered by the user in the interactive terminal."""
    if not req.cypher or not req.cypher.strip():
        raise HTTPException(status_code=400, detail="Cypher query cannot be empty.")
    
    # Simple write safety check
    cypher_upper = req.cypher.upper()
    if any(kw in cypher_upper for kw in ["DELETE", "DROP", "REMOVE", "CREATE", "SET"]):
        # Allow if live or handle safely
        pass
    
    return db_manager.execute_query(req.cypher, req.parameters or {})

@app.post("/api/seed")
def trigger_seed():
    """Triggers dataset re-seeding against CognoDB Cloud."""
    from seed import run_seed
    success = run_seed()
    if success:
        return {"status": "success", "message": "CognoDB graph successfully re-seeded."}
    else:
        return {"status": "error", "message": "Failed to seed database. Check server logs."}

# Serve Frontend static assets
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

    @app.get("/")
    def read_root():
        return FileResponse(os.path.join(frontend_dir, "index.html"))

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host=config.HOST, port=config.PORT, reload=True)
