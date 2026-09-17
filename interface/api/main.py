"""
BTS Aviation Delay Intelligence System
AI Analyst Interface — Text to SQL
Author: Narsing Shiva Kumar
"""

import os
import json
import logging
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from databricks import sql as databricks_sql
from openai import OpenAI

load_dotenv()

# ─── Logging ──────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── FastAPI App ──────────────────────────────────────────────
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

# ─── Config ───────────────────────────────────────────────────
DATABRICKS_HOST     = os.getenv("DATABRICKS_HOST", "adb-7405619816054217.17.azuredatabricks.net")
DATABRICKS_HTTP     = os.getenv("DATABRICKS_HTTP", "/sql/1.0/warehouses/25c8c0d2c506d054")
DATABRICKS_TOKEN    = os.getenv("DATABRICKS_TOKEN")
OPENAI_API_KEY      = os.getenv("OPENAI_API_KEY")
CATALOG             = "bts_databricks_eus"
SCHEMA              = "bts_gold"

client = OpenAI(api_key=OPENAI_API_KEY)

# ─── Semantic Layer System Prompt ─────────────────────────────
SYSTEM_PROMPT = """
You are the BTS Aviation Delay Intelligence Analyst.
You answer questions about US domestic airline delays using
data from 20,928,599 flights — January 2023 to December 2025.

== PLATFORM BOUNDARY ==
SUPPORTED:
- Historical delay analysis (2023-2025)
- Carrier performance comparison
- Airport and route exposure
- Delay cause distribution
- Cost sensitivity (modeled estimates)
- Seasonal and temporal patterns
- Tail number / aircraft analysis

NOT SUPPORTED:
- Real-time or live data
- Future predictions
- Passenger-level impact
- Actual airline financial costs
- Causation claims (only correlation/reporting)

== DATABASE SCHEMA ==
Catalog: bts_databricks_eus
Schema: bts_gold

TABLES:
1. fact_delays (20,928,599 rows)
   - flight_id, date_key, carrier_key, origin_airport_key
   - dest_airport_key, aircraft_key, flight_date
   - carrier_code, flight_number, origin_airport, dest_airport
   - tail_number, arr_delayed_flag (1=delayed,0=not,NULL=cancelled)
   - is_cancelled (1/0), is_diverted (1/0)
   - arr_delay_mins (signed, NULL=cancelled)
   - dep_delay_mins (signed, NULL=cancelled)
   - carrier_delay_mins, weather_delay_mins, nas_delay_mins
   - security_delay_mins, late_aircraft_delay_mins
   - dominant_delay_pillar (Safety/Legality/Efficiency/None) [DERIVED]
   - operational_influence_class (INTERNAL_ASSOCIATED/EXTERNAL_ASSOCIATED/MIXED/UNKNOWN) [DERIVED]
   - cancellation_code (A=Carrier,B=Weather,C=NAS,D=Security)
   - distance_miles, air_time_mins
   - flight_year, flight_month (partition columns)

2. dim_carrier (16 rows including UNKNOWN)
   - carrier_key, carrier_code, carrier_name
   - record_type (SNAPSHOT_V1 or UNKNOWN_MEMBER)

3. dim_airport (363 rows including UNKNOWN)
   - airport_key, airport_code, city, state
   - record_type (SNAPSHOT_V1 or UNKNOWN_MEMBER)
   - ROLE-PLAYING: used as origin AND destination in fact_delays

4. dim_date (1,097 rows)
   - date_key (YYYYMMDD), full_date, year, quarter
   - month, month_name, day_of_week (1=Sunday,7=Saturday)
   - is_weekend, season (Winter/Spring/Summer/Fall)
   - holiday_travel_window (Thanksgiving/Christmas/NewYear/July4th/LaborDay/MemorialDay/NULL)
   - record_type (STATIC or UNKNOWN_MEMBER)

5. dim_aircraft (6,685 rows including UNKNOWN)
   - aircraft_key, tail_number
   - record_type (SNAPSHOT_V1 or UNKNOWN_MEMBER)

6. dim_delay_reason (6 rows)
   - delay_reason_key, delay_code, delay_category
   - ioc_pillar (Safety/Legality/Efficiency) [DERIVED - project-defined]
   - operational_influence_class [DERIVED]

7. bridge_flight_delay_reason (7,072,280 rows)
   - flight_id, delay_reason_key, delay_code
   - attributed_mins, attribution_pct
   - NOTE: Only flights with >=1 non-NULL delay cause appear here
   - WARNING: Never SUM attributed_mins across multiple delay_codes without filtering

8. model_delay_cost (20,928,599 rows)
   - flight_id, estimated_delay_cost (arr_delay_abs_mins * 45)
   - evidence_state = 'MODELED'
   - Source: Ferguson et al. FAA/NEXTOR 2010

== CERTIFIED JOINS ==
- fact_delays[date_key] -> dim_date[date_key]
- fact_delays[carrier_key] -> dim_carrier[carrier_key]
- fact_delays[origin_airport_key] -> dim_airport[airport_key] (origin role)
- fact_delays[dest_airport_key] -> dim_airport[airport_key] (destination role)
- fact_delays[aircraft_key] -> dim_aircraft[aircraft_key]
- fact_delays[flight_id] -> bridge_flight_delay_reason[flight_id]
- bridge_flight_delay_reason[delay_reason_key] -> dim_delay_reason[delay_reason_key]
- fact_delays[flight_id] -> model_delay_cost[flight_id]

== CRITICAL SQL RULES ==
1. ALWAYS filter dim_carrier: WHERE c.record_type = 'SNAPSHOT_V1'
2. ALWAYS filter dim_airport: WHERE a.record_type = 'SNAPSHOT_V1'
3. ALWAYS filter dim_date: WHERE d.record_type = 'STATIC'
4. Delay Rate = delayed_flights / operated_flights (NOT total flights)
   operated_flights = COUNT(*) WHERE is_cancelled = 0
5. NULL in arr_delay_mins = cancelled flight. NEVER impute.
6. NULL in delay cause columns = BTS did not report. NOT zero.
7. For delay cause analysis, use bridge table and filter by ONE delay_code
8. Use full table names: bts_databricks_eus.bts_gold.fact_delays
9. LIMIT results to max 20 rows unless user asks for more
10. Always use ROUND() for percentages and float values

== EVIDENCE FRAMEWORK ==
Label every claim with:
- OBSERVED: directly from BTS source data
- DERIVED: calculated using project-defined logic
- MODELED: based on external assumption ($45/min Ferguson et al.)
- INFERRED: pattern interpretation, not proven causation
- UNKNOWN: cannot be determined from this data

== YOUR RESPONSE FORMAT ==
Always respond in this JSON format:
{
  "sql": "the SQL query you generated (or null if not applicable)",
  "interpretation": "plain English interpretation of what the SQL answers",
  "evidence_notes": "what evidence classification applies",
  "platform_boundary": "any limitations that apply to this question",
  "follow_up_suggestions": ["suggestion 1", "suggestion 2", "suggestion 3"]
}

If the question is outside platform boundary, set sql to null and explain clearly.
If you cannot generate valid SQL, set sql to null and explain why.
Keep SQL clean and executable. No markdown code blocks in SQL.
"""

# ─── Models ───────────────────────────────────────────────────
class QuestionRequest(BaseModel):
    question: str
    max_rows: Optional[int] = 20

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

# ─── Databricks Query ─────────────────────────────────────────
def run_databricks_query(sql: str, max_rows: int = 20) -> dict:
    """Execute SQL against Databricks Gold layer."""
    import time
    start = time.time()

    try:
        with databricks_sql.connect(
            server_hostname=DATABRICKS_HOST,
            http_path=DATABRICKS_HTTP,
            access_token=DATABRICKS_TOKEN
        ) as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql)
                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchmany(max_rows)
                results = [dict(zip(columns, row)) for row in rows]
                elapsed = int((time.time() - start) * 1000)
                return {
                    "results": results,
                    "row_count": len(results),
                    "execution_time_ms": elapsed,
                    "error": None
                }
    except Exception as e:
        logger.error(f"Databricks query error: {e}")
        return {
            "results": None,
            "row_count": 0,
            "execution_time_ms": None,
            "error": str(e)
        }

# ─── AI SQL Generation ────────────────────────────────────────
def generate_sql_and_interpretation(question: str) -> dict:
    """Use GPT to generate SQL and interpretation."""
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

        # Parse JSON response
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]

        parsed = json.loads(content)
        return parsed

    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}, content: {content}")
        return {
            "sql": None,
            "interpretation": "I encountered an error processing your question.",
            "evidence_notes": "UNKNOWN",
            "platform_boundary": "System error — please try again.",
            "follow_up_suggestions": []
        }
    except Exception as e:
        logger.error(f"OpenAI error: {e}")
        return {
            "sql": None,
            "interpretation": f"AI service error: {str(e)}",
            "evidence_notes": "UNKNOWN",
            "platform_boundary": "System error — please try again.",
            "follow_up_suggestions": []
        }

# ─── Format Results ───────────────────────────────────────────
def format_results_for_response(results: list) -> list:
    """Convert results to JSON-serializable format."""
    if not results:
        return []
    formatted = []
    for row in results:
        formatted_row = {}
        for key, value in row.items():
            if hasattr(value, 'isoformat'):
                formatted_row[key] = value.isoformat()
            elif value is None:
                formatted_row[key] = None
            else:
                formatted_row[key] = value
        formatted.append(formatted_row)
    return formatted

# ─── Routes ───────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <html>
    <head><title>BTS Aviation AI Analyst</title></head>
    <body style="font-family:monospace;background:#0d1117;color:#e6edf3;padding:2rem;">
    <h1>✈ BTS Aviation Delay Intelligence API</h1>
    <p>20.9M US flight records | Jan 2023 – Dec 2025</p>
    <p><a href="/docs" style="color:#388bfd;">API Documentation →</a></p>
    <p><a href="/health" style="color:#388bfd;">Health Check →</a></p>
    </body>
    </html>
    """

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
    """
    Ask any question about US airline delays (2023-2025).
    The AI generates SQL, queries Gold layer, and returns evidence-labeled results.
    """
    logger.info(f"Question: {request.question}")

    # Step 1: Generate SQL using GPT
    ai_response = generate_sql_and_interpretation(request.question)

    sql = ai_response.get("sql")
    interpretation = ai_response.get("interpretation", "")
    evidence_notes = ai_response.get("evidence_notes", "")
    platform_boundary = ai_response.get("platform_boundary", "")
    follow_ups = ai_response.get("follow_up_suggestions", [])

    # Step 2: Execute SQL if generated
    results = None
    row_count = None
    execution_time_ms = None
    error = None

    if sql:
        query_result = run_databricks_query(sql, request.max_rows)
        results = format_results_for_response(query_result["results"])
        row_count = query_result["row_count"]
        execution_time_ms = query_result["execution_time_ms"]
        error = query_result["error"]

        if error:
            interpretation = f"SQL generated but execution failed: {error}"

    return AnalystResponse(
        question=request.question,
        sql=sql,
        results=results,
        row_count=row_count,
        interpretation=interpretation,
        evidence_notes=evidence_notes,
        platform_boundary=platform_boundary,
        follow_up_suggestions=follow_ups,
        execution_time_ms=execution_time_ms,
        error=error
    )

@app.get("/schema")
async def get_schema():
    """Returns the Gold layer schema summary."""
    return {
        "catalog": CATALOG,
        "schema": SCHEMA,
        "tables": {
            "fact_delays": {"rows": 20928599, "grain": "one flight per day"},
            "dim_carrier": {"rows": 16, "note": "15 carriers + 1 UNKNOWN"},
            "dim_airport": {"rows": 363, "note": "362 airports + 1 UNKNOWN"},
            "dim_date": {"rows": 1097, "note": "Jan 2023 - Dec 2025"},
            "dim_aircraft": {"rows": 6685, "note": "6684 tail numbers + 1 UNKNOWN"},
            "dim_delay_reason": {"rows": 6, "note": "5 BTS codes + 1 UNKNOWN"},
            "bridge_flight_delay_reason": {"rows": 7072280},
            "model_cost_scenario": {"rows": 1, "note": "$45/min Ferguson et al."},
            "model_delay_cost": {"rows": 20928599, "evidence": "MODELED"}
        },
        "evidence_framework": ["OBSERVED", "DERIVED", "MODELED", "INFERRED", "UNKNOWN"],
        "platform_boundary": {
            "supported": [
                "Historical delay analysis (2023-2025)",
                "Carrier performance comparison",
                "Airport and route exposure",
                "Delay cause distribution",
                "Cost sensitivity (modeled)",
                "Seasonal patterns",
                "Tail number analysis"
            ],
            "not_supported": [
                "Real-time or live data",
                "Future predictions",
                "Passenger-level impact",
                "Actual airline financial costs",
                "Causation claims"
            ]
        }
    }
