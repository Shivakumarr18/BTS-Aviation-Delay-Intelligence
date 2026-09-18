"""
BTS Aviation Delay Intelligence System
AI Analyst Interface — Text to SQL
Author: Narsing Shiva Kumar
"""

import os
import json
import time
import logging
import requests
from typing import Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="BTS Aviation Delay Intelligence API",
    description="AI Analyst interface for 20.9M US flight records (2023-2025)",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABRICKS_HOST  = os.getenv("DATABRICKS_HOST", "adb-7405619816054217.17.azuredatabricks.net")
DATABRICKS_HTTP  = os.getenv("DATABRICKS_HTTP", "/sql/1.0/warehouses/25c8c0d2c506d054")
DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN")
OPENAI_API_KEY   = os.getenv("OPENAI_API_KEY")
WAREHOUSE_ID     = DATABRICKS_HTTP.split("/")[-1] if DATABRICKS_HTTP else ""

client = OpenAI(api_key=OPENAI_API_KEY)

SYSTEM_PROMPT = """
You are the BTS Aviation Delay Intelligence Analyst.
You answer questions about US domestic airline delays using
data from 20,928,599 flights — January 2023 to December 2025.

== PLATFORM BOUNDARY ==
SUPPORTED: Historical delay analysis (2023-2025), carrier performance,
airport exposure, delay causes, cost sensitivity, seasonal patterns, tail number analysis.
NOT SUPPORTED: Real-time data, future predictions, passenger impact,
actual airline costs, causation claims.

== DATABASE SCHEMA ==
Catalog: bts_databricks_eus  Schema: bts_gold

TABLES:
1. fact_delays (20,928,599 rows)
   - flight_id, date_key, carrier_key, origin_airport_key, dest_airport_key
   - aircraft_key, flight_date, carrier_code, flight_number
   - origin_airport, dest_airport, tail_number
   - arr_delayed_flag (1=delayed,0=not,NULL=cancelled)
   - is_cancelled (1/0), is_diverted (1/0)
   - arr_delay_mins (signed, NULL=cancelled), dep_delay_mins
   - carrier_delay_mins, weather_delay_mins, nas_delay_mins
   - security_delay_mins, late_aircraft_delay_mins
   - dominant_delay_pillar (Safety/Legality/Efficiency/None) [DERIVED]
   - operational_influence_class [DERIVED]
   - cancellation_code (A=Carrier,B=Weather,C=NAS,D=Security)
   - distance_miles, air_time_mins, flight_year, flight_month

2. dim_carrier (16 rows): carrier_key, carrier_code, carrier_name, record_type
3. dim_airport (363 rows): airport_key, airport_code, city, state, record_type
4. dim_date (1097 rows): date_key, full_date, year, quarter, month, month_name,
   day_of_week(1=Sun,7=Sat), is_weekend, season, holiday_travel_window, record_type
5. dim_aircraft (6685 rows): aircraft_key, tail_number, record_type
6. dim_delay_reason (6 rows): delay_reason_key, delay_code, delay_category, ioc_pillar
7. bridge_flight_delay_reason (7,072,280 rows): flight_id, delay_reason_key,
   delay_code, attributed_mins, attribution_pct
8. model_delay_cost (20,928,599 rows): flight_id, estimated_delay_cost, evidence_state='MODELED'

== CRITICAL SQL RULES ==
1. ALWAYS filter: WHERE c.record_type = 'SNAPSHOT_V1' for dim_carrier
2. ALWAYS filter: WHERE a.record_type = 'SNAPSHOT_V1' for dim_airport
3. ALWAYS filter: WHERE d.record_type = 'STATIC' for dim_date
4. Delay Rate = SUM(arr_delayed_flag) / COUNT(*) WHERE is_cancelled = 0
5. NULL arr_delay_mins = cancelled. NEVER impute.
6. Use full table names: bts_databricks_eus.bts_gold.fact_delays
7. LIMIT results to max 20 rows
8. Always ROUND() floats to 2 decimal places
9. For cost values: ROUND(SUM(estimated_delay_cost)/1000000000, 2) AS cost_billions_usd
10. For delay rates: ROUND(100.0 * SUM(arr_delayed_flag) / COUNT(*), 2) AS delay_rate_pct
10a.In interpretation text, always state the actual computed value, 
never use placeholder text like XX.XX% or X.XX billion.
11. NEVER return scientific notation. Always return human-readable numbers.
12. Format large numbers with commas in interpretation text only.
13.CRITICAL RULE — NO INDEPENDENT CALCULATION:
When query results are returned, ALWAYS use the exact 
numbers from the result in your interpretation.
NEVER calculate, estimate, or derive numbers independently.
If result shows cost_billions_usd = 14.95, say exactly 
"14.95 billion USD" in interpretation.
If result shows delay_rate_pct = 21.18, say exactly 
"21.18%" in interpretation.
The query result is the source of truth. Not your training data.
14.When writing interpretation, do NOT state specific numbers.
Say: "Based on the query results shown above" instead.
The user can read the numbers directly from the results table.

== COLUMNS THAT DO NOT EXIST — NEVER USE ==
- aircraft_type (no aircraft type/model/manufacturer in BTS)
- passenger_count (no passenger data in BTS)
- gate_number (not in dataset)
- fuel_cost (not in dataset)
- actual_cost (not in dataset — only modeled estimates)
- flight_status (not in dataset)
If asked about any of these → explicitly state the column does not exist
in BTS TranStats, then offer the closest available alternative.

== AIRCRAFT TYPE HANDLING ==
dim_aircraft contains ONLY tail_number. There is NO aircraft_type,
manufacturer, model, age, or fleet data.
If asked about aircraft type → say: "Aircraft type/model data is not 
available in BTS TranStats. I can show delay patterns by tail number instead."
NEVER silently substitute tail_number for aircraft_type.

== NUMBER FORMATTING IN INTERPRETATION ==
- Costs: always say "X.XX billion USD" not scientific notation
- Delay rates: always say "XX.XX%" not decimals like 0.2118
- Flight counts: use commas e.g. "20,928,599 flights"
- Delay minutes: use millions e.g. "152.6 million delay minutes"

== EVIDENCE LABEL RULES ==
- arr_delay_mins, carrier_code, is_cancelled → OBSERVED
- dominant_delay_pillar, operational_influence_class → DERIVED
- estimated_delay_cost → always MODELED
- seasonal patterns from dim_date → OBSERVED
- ioc_pillar from dim_delay_reason → DERIVED

== EVIDENCE FRAMEWORK ==
OBSERVED: directly from BTS source
DERIVED: calculated using project-defined logic
MODELED: based on external assumption ($45/min Ferguson et al.)
INFERRED: pattern interpretation, not proven
UNKNOWN: cannot be determined

== RESPONSE FORMAT ==
Respond ONLY in valid JSON:
{
  "sql": "executable SQL query or null",
  "interpretation": "plain English answer",
  "evidence_notes": "evidence classification",
  "platform_boundary": "limitations or empty string",
  "follow_up_suggestions": ["suggestion1", "suggestion2", "suggestion3"]
}
"""

class QuestionRequest(BaseModel):
    question: str
    max_rows: Optional[int] = 15

class AnalystResponse(BaseModel):
    question: str
    sql: Optional[str]
    results: Optional[list]
    row_count: Optional[int]
    interpretation: str
    evidence_notes: str
    platform_boundary: str
    follow_up_suggestions: list
    execution_time_ms: Optional[int]
    error: Optional[str]

def run_databricks_query(sql: str, max_rows: int = 15) -> dict:
    """Execute SQL via Databricks SQL Statement API."""
    start = time.time()
    headers = {
        "Authorization": f"Bearer {DATABRICKS_TOKEN}",
        "Content-Type": "application/json"
    }
    url = f"https://{DATABRICKS_HOST}/api/2.0/sql/statements"
    payload = {
        "statement": sql,
        "warehouse_id": WAREHOUSE_ID,
        "wait_timeout": "50s",
        "on_wait_timeout": "CONTINUE",
        "row_limit": max_rows
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        data = response.json()

        # Poll if still running
        stmt_id = data.get("statement_id")
        status = data.get("status", {}).get("state", "")
        max_polls = 10
        polls = 0
        while status in ("PENDING", "RUNNING") and polls < max_polls:
            time.sleep(3)
            r = requests.get(f"{url}/{stmt_id}", headers=headers, timeout=30)
            data = r.json()
            status = data.get("status", {}).get("state", "")
            polls += 1

        if status != "SUCCEEDED":
            error = data.get("status", {}).get("error", {}).get("message", "Query failed")
            return {"results": None, "row_count": 0, "execution_time_ms": None, "error": error}

        # Parse results
        manifest = data.get("manifest", {})
        result = data.get("result", {})
        columns = [col["name"] for col in manifest.get("schema", {}).get("columns", [])]
        rows = result.get("data_array", [])
        results = [dict(zip(columns, row)) for row in rows]
        elapsed = int((time.time() - start) * 1000)
        return {"results": results, "row_count": len(results), "execution_time_ms": elapsed, "error": None}

    except Exception as e:
        logger.error(f"Databricks error: {e}")
        return {"results": None, "row_count": 0, "execution_time_ms": None, "error": str(e)}

def generate_sql_and_interpretation(question: str) -> dict:
    """Use GPT to generate SQL."""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Question: {question}"}
            ],
            temperature=0.1,
            max_tokens=1500
        )
        content = response.choices[0].message.content.strip()
        if "```" in content:
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        return json.loads(content)
    except Exception as e:
        logger.error(f"OpenAI error: {e}")
        return {
            "sql": None,
            "interpretation": f"AI service error: {str(e)}",
            "evidence_notes": "UNKNOWN",
            "platform_boundary": "System error — please try again.",
            "follow_up_suggestions": []
        }

def format_results(results: list) -> list:
    if not results:
        return []
    formatted = []
    for row in results:
        formatted_row = {}
        for k, v in row.items():
            if hasattr(v, 'isoformat'):
                formatted_row[k] = v.isoformat()
            else:
                formatted_row[k] = v
        formatted.append(formatted_row)
    return formatted

@app.get("/", response_class=HTMLResponse)
async def root():
    return """<html><body style="font-family:monospace;background:#0d1117;color:#e6edf3;padding:2rem;">
    <h1>✈ BTS Aviation Delay Intelligence API</h1>
    <p>20.9M US flight records | Jan 2023 – Dec 2025</p>
    <p><a href="/docs" style="color:#388bfd;">API Documentation →</a></p>
    <p><a href="/health" style="color:#388bfd;">Health Check →</a></p>
    </body></html>"""

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "system": "BTS Aviation Delay Intelligence API",
        "version": "1.0.0",
        "data": "20,928,599 flights | Jan 2023 - Dec 2025",
        "platform_boundary": "Historical analysis only. No real-time data."
    }

@app.post("/ask", response_model=AnalystResponse)
async def ask_analyst(request: QuestionRequest):
    logger.info(f"Question: {request.question}")
    ai_response = generate_sql_and_interpretation(request.question)
    sql = ai_response.get("sql")
    results = None
    row_count = None
    execution_time_ms = None
    error = None
    if sql:
        query_result = run_databricks_query(sql, request.max_rows)
        results = format_results(query_result["results"] or [])
        row_count = query_result["row_count"]
        execution_time_ms = query_result["execution_time_ms"]
        error = query_result["error"]
        if error:
            ai_response["interpretation"] += f" (Query error: {error})"
    return AnalystResponse(
        question=request.question,
        sql=sql,
        results=results,
        row_count=row_count,
        interpretation=ai_response.get("interpretation", ""),
        evidence_notes=ai_response.get("evidence_notes", ""),
        platform_boundary=ai_response.get("platform_boundary", ""),
        follow_up_suggestions=ai_response.get("follow_up_suggestions", []),
        execution_time_ms=execution_time_ms,
        error=error
    )

@app.get("/schema")
async def get_schema():
    return {
        "catalog": "bts_databricks_eus",
        "schema": "bts_gold",
        "tables": {
            "fact_delays": {"rows": 20928599},
            "dim_carrier": {"rows": 16},
            "dim_airport": {"rows": 363},
            "dim_date": {"rows": 1097},
            "dim_aircraft": {"rows": 6685},
            "dim_delay_reason": {"rows": 6},
            "bridge_flight_delay_reason": {"rows": 7072280},
            "model_delay_cost": {"rows": 20928599, "evidence": "MODELED"}
        }
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
