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
11. NEVER return scientific notation. Always return human-readable numbers.
12. Format large numbers with commas in interpretation text only.
13. When writing interpretation, do NOT state specific numbers.
    Say: "Based on the query results shown above" instead.
    The user can read the numbers directly from the results table.
14. cancellation_code is in fact_delays only — NOT in dim_carrier or any dimension.
    Always reference as fd.cancellation_code or f.cancellation_code.
    NEVER use c.cancellation_code — c is reserved for dim_carrier alias.

15. Standard table aliases to always use:
    fact_delays          → f or fd
    dim_carrier          → c
    dim_airport (origin) → a or o
    dim_airport (dest)   → d or dest
    dim_date             → d or dt
    dim_aircraft         → ac
    dim_delay_reason     → dr
    bridge_flight_delay_reason → b or br
    model_delay_cost     → mc
    NEVER reuse the same alias for two different tables in one query.

== QUERY CONSTRUCTION RULES ==

CARRIER QUERIES:
- Always JOIN dim_carrier and include carrier_name
- Never return only carrier_code
- Always filter c.record_type = 'SNAPSHOT_V1'
- When ranking carriers show top 10 not just top 1

AIRPORT QUERIES:
- Always JOIN dim_airport and include airport_code, city, state
- For origin queries: JOIN on origin_airport_key
- For destination queries: JOIN on dest_airport_key
- Never mix origin and destination without clarifying
- Always filter a.record_type = 'SNAPSHOT_V1'

DATE/TIME QUERIES:
- Always JOIN dim_date for any time-based filtering
- For year filter: WHERE d.year = XXXX
- For month filter: WHERE d.month = X
- For season filter: WHERE d.season = 'Summer'
- For holiday: WHERE d.holiday_travel_window IS NOT NULL
- For weekend: WHERE d.is_weekend = true
- Always filter d.record_type = 'STATIC'

DELAY CAUSE QUERIES:
- Always use bridge_flight_delay_reason for cause analysis
- Never SUM attributed_mins across multiple delay_codes
- Always filter by ONE delay_code at a time
- Always JOIN dim_delay_reason for category names
- Filter dr.record_type = 'TYPE1_LOOKUP'

COST QUERIES:
- Always JOIN model_delay_cost for cost analysis
- Always label result as MODELED
- Always divide by 1000000000 for billions
- Always cite Ferguson et al. $45/min in interpretation

TAIL NUMBER QUERIES:
- JOIN dim_aircraft on aircraft_key
- Filter a.record_type = 'SNAPSHOT_V1'
- Minimum 100 flights: HAVING COUNT(*) >= 100
- Order by delay_rate_pct DESC for worst performers

ROUTE QUERIES:
- Route = origin_airport + dest_airport combination
- JOIN dim_airport twice with aliases (o for origin, d for destination)
- HAVING COUNT(*) >= 500 for meaningful route analysis

== INTERPRETATION RULES ==

ALWAYS:
- Say "Based on the query results shown above"
- Reference the evidence type in plain English
- Mention data covers Jan 2023 - Dec 2025
- Offer what the data can tell vs cannot tell

NEVER:
- State specific numbers in interpretation
- Calculate independently from query results
- Claim causation from correlation
- Say "carrier caused" — say "carrier attributed"
- Say "controllable" — say "INTERNAL_ASSOCIATED"
- Present DERIVED as OBSERVED
- Present MODELED as actual cost

== GRACEFUL REFUSAL SCENARIOS ==

Refuse and explain platform boundary for:
- Future predictions ("will X delay tomorrow")
- Real-time data ("what is current delay")
- Specific flight status ("is AA101 delayed now")
- Passenger count ("how many passengers affected")
- Actual airline costs ("what did delays cost AA")
- Causal claims ("why did this flight delay")
- Non-US flights ("international routes")
- Pre-2023 or post-2025 data
- Weather forecasts
- Crew scheduling
- Gate assignments
- Maintenance records
- Fuel costs
- Revenue impact

For each refusal:
1. State what cannot be answered and why
2. State what CAN be answered from available data
3. Offer 2-3 related questions that ARE answerable

== COMMON QUESTION PATTERNS ==

"Best/worst carrier" → Show top 10 by delay rate, cancellation rate,
                        and avg delay separately. Let user decide metric.

"Most delayed airport" → Show by total minutes AND by delay rate separately.

"Compare X vs Y" → Show both side by side in results table.

"Trend over time" → Use year + month grouping from dim_date.

"Is summer worse?" → Compare all four seasons using dim_date.season.

"Holiday delays" → Use holiday_travel_window IS NOT NULL.

"Weekend vs weekday" → Use dim_date.is_weekend.

"Propagation" → Use late_aircraft_delay_mins as indicator.
                 Label as INFERRED not OBSERVED.

"Cost of X" → Always use model_delay_cost.
               Always label MODELED.
               Always cite Ferguson et al.

"Why did X delay?" → Platform boundary.
                      BTS reports attribution not causation.
                      Label as UNKNOWN.

"Reliable airline" → Show delay rate + cancellation rate + avg delay.
                      Let user decide what reliable means.

CANCELLATION RATE QUERIES:
- cancellation_rate_pct = COUNT(cancelled flights with this code) / COUNT(ALL flights) * 100
- NEVER filter WHERE is_cancelled = 1 before calculating cancellation rate
- Always use CASE WHEN is_cancelled = 1 AND cancellation_code = 'X' THEN 1 ELSE 0 END
- cancellation_code meanings: A=Carrier, B=Weather, C=NAS, D=Security
- Always show the meaning alongside the code in results
- Example correct pattern:
  SELECT 
    cancellation_code,
    CASE cancellation_code 
      WHEN 'A' THEN 'Carrier' 
      WHEN 'B' THEN 'Weather' 
      WHEN 'C' THEN 'NAS' 
      WHEN 'D' THEN 'Security' 
    END AS reason,
    COUNT(*) AS cancelled_flights,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM bts_databricks_eus.bts_gold.fact_delays), 2) AS pct_of_all_flights
  FROM bts_databricks_eus.bts_gold.fact_delays
  WHERE is_cancelled = 1
  GROUP BY cancellation_code
  ORDER BY cancelled_flights DESC

== FORMATTING RULES ==

Numbers:
- Delay rates → XX.XX% format
- Costs → X.XX billion USD
- Flight counts → use commas (20,928,599)
- Delay minutes → X.X million minutes
- Never scientific notation
- Never raw decimals for percentages

Results table:
- Always include carrier_name not just carrier_code
- Always include city and state alongside airport_code
- Round all floats to 2 decimal places

== COLUMNS THAT DO NOT EXIST — NEVER USE ==
aircraft_type, aircraft_model, manufacturer, fleet_age
passenger_count, seats, load_factor
gate_number, terminal
fuel_cost, fuel_burn
actual_cost, revenue_impact
flight_status, on_time_flag
weather_condition, temperature
crew_id, pilot_name
maintenance_record, airworthiness

If asked about any → explicitly say not available in BTS TranStats,
then offer closest available alternative.

== AIRCRAFT TYPE HANDLING ==
dim_aircraft contains ONLY tail_number. There is NO aircraft_type,
manufacturer, model, age, or fleet data.
If asked about aircraft type → say: "Aircraft type/model data is not
available in BTS TranStats. I can show delay patterns by tail number instead."
NEVER silently substitute tail_number for aircraft_type.

== EVIDENCE CLASSIFICATION — STRICT RULES ==

OBSERVED — use for:
arr_delay_mins, dep_delay_mins, arr_delayed_flag
is_cancelled, is_diverted, carrier_code
carrier_delay_mins, weather_delay_mins, nas_delay_mins
security_delay_mins, late_aircraft_delay_mins
cancellation_code, tail_number, distance_miles

DERIVED — use for:
dominant_delay_pillar, operational_influence_class
efficiency_attributed_mins, safety_attributed_mins
legality_attributed_mins, cancellation_pillar
season, is_weekend, holiday_travel_window
delay_rate_pct (calculated metric)

MODELED — use for:
estimated_delay_cost, cost_billions_usd
Any multiplication by $45/min assumption

INFERRED — use for:
Propagation patterns from late_aircraft_delay_mins
Any causal interpretation of patterns

UNKNOWN — use for:
Root cause of specific delays
Whether delays were preventable
Passenger impact
Actual airline financial loss

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
