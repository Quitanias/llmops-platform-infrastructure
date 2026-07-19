import os
import json
import asyncio
import logging
from fastapi import FastAPI, HTTPException, UploadFile, File, Response, status
from pydantic import BaseModel
from groq import Groq
import asyncpg
from sentence_transformers import SentenceTransformer

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("llmops-platform")

app = FastAPI(title="LLMOps Agent API - Enterprise Cloud Architecture")

# --- Environment & Security Verifications ---
API_KEY = os.getenv("GROQ_API_KEY")
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME", "sre_vector_manual")
DB_USER = os.getenv("DB_USER", "db_admin")
DB_PASSWORD = os.getenv("DB_PASSWORD")

if not API_KEY or not DB_HOST or not DB_PASSWORD:
    raise ValueError("Missing critical environment variables (GROQ_API_KEY, DB_HOST, DB_PASSWORD).")

groq_client = Groq(api_key=API_KEY)

# --- 1. LOCAL EMBEDDING ENGINE INITIALIZATION ---
# Loaded globally. The Kubernetes startupProbe handles this cold start time.
logger.info("Initializing Local SentenceTransformer Model...")
embedding_model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
logger.info("Embedding Model successfully loaded into memory.")


# --- 2. DATABASE CONNECTION & INITIALIZATION ---
async def init_db():
    """Initializes the PostgreSQL database and enables the pgvector extension."""
    conn = await asyncpg.connect(
        host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD
    )
    try:
        # Enable pgvector extension in the RDS cluster
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        
        # Create table for documentation chunks with a 384-dimension vector column
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS sre_knowledge_base (
                id SERIAL PRIMARY KEY,
                filename TEXT,
                chunk_content TEXT,
                embedding vector(384)
            );
        """)
        logger.info("PostgreSQL Vector DB structures verified/created successfully.")
    finally:
        await conn.close()

@app.on_event("startup")
async def startup_event():
    await init_db()


# --- 3. AGENT TOOLS (DATABASE DRIVEN) ---
async def search_vector_db(query: str) -> str:
    """Tool: Generates embeddings for the query and searches the PostgreSQL Vector Database"""
    logger.info(f"[Tool Called] Searching Vector DB for: {query}")
    
    # Generate embedding vector locally from text
    query_vector = embedding_model.encode(query).tolist()
    
    conn = await asyncpg.connect(
        host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD
    )
    try:
        # SRE Performance Query: Cosine Distance (<=> operator) to fetch top 3 chunks
        rows = await conn.fetch("""
            SELECT chunk_content 
            FROM sre_knowledge_base 
            ORDER BY embedding <=> $1::vector 
            LIMIT 3;
        """, str(query_vector))
        
        if not rows:
            return "No information found in the internal documentation database."
            
        context_chunks = [row['chunk_content'] for row in rows]
        return "\n---\n".join(context_chunks)
    except Exception as e:
        logger.error(f"Database query failure: {str(e)}")
        return f"Error querying internal database: {str(e)}"
    finally:
        await conn.close()

def query_prometheus_metrics(query: str, time_range: str) -> str:
    """Tool: Simulates fetching metrics from Prometheus (HPA, CPU, Memory)."""
    logger.info(f"[Tool Called] Querying Prometheus: {query} for range {time_range}")
    # AIOps Simulation: In a real environment, we would use httpx to fetch from Prometheus API
    if "hpa" in query.lower() or "memory" in query.lower() or "cpu" in query.lower():
        return json.dumps({
            "status": "success",
            "data": {
                "resultType": "matrix",
                "result": [
                    {
                        "metric": {"pod": "fastapi-app-pod-1234", "namespace": "production"},
                        "values": [
                            [1715000000, "0.95"], # High CPU
                            [1715000060, "0.98"], # High CPU -> HPA Scale up trigger
                            [1715000120, "drop_detected"] # Pod terminated by OOM or eviction
                        ]
                    }
                ]
            },
            "summary": "CPU/Memory spike detected in the last few minutes. HPA triggered pod eviction/restart."
        })
    return json.dumps({"status": "success", "data": [], "summary": "No metric anomalies detected for the query."})

def query_loki_logs(query: str, limit: int = 50) -> str:
    """Tool: Simulates fetching recent logs from Loki/CloudWatch."""
    logger.info(f"[Tool Called] Querying Loki for logs: {query} (limit {limit})")
    # Simulation of logs explaining the FastAPI cold start latency
    if "fastapi" in query.lower() or "error" in query.lower():
        return json.dumps({
            "status": "success",
            "logs": [
                "[ERROR] Pod fastapi-app-pod-1234 terminated unexpectedly (OOMKilled).",
                "[INFO] Starting new container fastapi-app-pod-5678...",
                "[INFO] Loading SentenceTransformer model 'paraphrase-multilingual-MiniLM-L12-v2' into memory...",
                "[WARN] startupProbe failed: connection refused.",
                "[INFO] SentenceTransformer model loaded successfully (took 180s).",
                "[INFO] Application startup complete."
            ],
            "summary": "The old pod crashed and the new one spent approximately 3 minutes stuck in startupProbe due to the heavy loading of the embedding model weights during cold start."
        })
    return json.dumps({"status": "success", "logs": []})

def query_git_history(service_name: str, limit: int = 5) -> str:
    """Tool: Simulates fetching recent Git commits and CI/CD deployments."""
    logger.info(f"[Tool Called] Querying Git History for: {service_name} (limit {limit})")
    if "fastapi" in service_name.lower() or "main.py" in service_name.lower() or "postgres" in service_name.lower():
        return json.dumps({
            "status": "success",
            "recent_commits": [
                {"commit": "a1b2c3d", "author": "devops-team", "message": "fix: update asyncpg connection pool initialization with no max limit"},
                {"commit": "e5f6g7h", "author": "dev-team", "message": "feat: integrate AWS Bedrock client for Claude 3.5"},
                {"commit": "i9j0k1l", "author": "sre-bot", "message": "chore: bump prometheus-client to 0.25.0"}
            ],
            "recent_deployments": [
                {"deploy_id": "deploy-992", "status": "SUCCESS", "timestamp": "20 minutes ago"}
            ],
            "summary": "A deployment occurred 20 minutes ago. The latest commit modified the asyncpg connection pool initialization."
        })
    return json.dumps({"status": "success", "recent_commits": [], "summary": "No recent changes found."})

def query_aws_health(service: str, region: str) -> str:
    """Tool: Simulates querying the AWS Health Dashboard for global outages."""
    logger.info(f"[Tool Called] Querying AWS Health for {service} in {region}")
    if "bedrock" in service.lower() or "claude" in service.lower() or "health" in service.lower():
        return json.dumps({
            "status": "success",
            "events": [
                {
                    "event_id": "AWS-BEDROCK-OUTAGE-123",
                    "service": "Amazon Bedrock",
                    "region": "us-east-1",
                    "status": "Open",
                    "description": "We are investigating increased API error rates and timeouts for Amazon Bedrock Claude models in the US-EAST-1 region."
                }
            ],
            "summary": "Active global outage reported for Amazon Bedrock in us-east-1."
        })
    return json.dumps({"status": "success", "events": [], "summary": "No operational issues reported by AWS."})

# Mapping for the Agent Execution Engine
async def execute_tool(name: str, arguments: dict) -> str:
    if name == "search_sre_manual":
        # Capture the query from arguments and route to async DB search
        return await search_vector_db(arguments.get("query", ""))
    elif name == "query_prometheus_metrics":
        return query_prometheus_metrics(arguments.get("query", ""), arguments.get("time_range", "10m"))
    elif name == "query_loki_logs":
        return query_loki_logs(arguments.get("query", ""), arguments.get("limit", 50))
    elif name == "query_git_history":
        return query_git_history(arguments.get("service_name", ""), arguments.get("limit", 5))
    elif name == "query_aws_health":
        return query_aws_health(arguments.get("service", ""), arguments.get("region", "us-east-1"))
    else:
        return f"Tool {name} not found."

tools_schema = [
    {
        "type": "function",
        "function": {
            "name": "search_sre_manual",
            "description": "Use to find information about Harness, deployments, pipelines, CI/CD, and corporate SRE rules/runbooks.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The specific technical term to look for."}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_prometheus_metrics",
            "description": "Fetch real-time metrics (CPU, Memory, HPA) from the Prometheus monitoring stack.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The PromQL query or resource name (e.g. 'fastapi memory hpa')."},
                    "time_range": {"type": "string", "description": "The time range for the query (e.g. '10m', '1h')."}
                },
                "required": ["query", "time_range"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_loki_logs",
            "description": "Fetch recent logs from Loki or CloudWatch for a specific service or error trace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The log search query or service name (e.g. 'fastapi error')."},
                    "limit": {"type": "integer", "description": "Maximum number of log lines to return."}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_git_history",
            "description": "Fetch recent GitHub commits and CI/CD deployment history for a specific repository or service.",
            "parameters": {
                "type": "object",
                "properties": {
                    "service_name": {"type": "string", "description": "The service name or repo file (e.g. 'fastapi' or 'main.py')."},
                    "limit": {"type": "integer", "description": "Maximum number of commits to fetch."}
                },
                "required": ["service_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_aws_health",
            "description": "Query the AWS Health Dashboard for global service outages or regional instabilities.",
            "parameters": {
                "type": "object",
                "properties": {
                    "service": {"type": "string", "description": "The AWS service name (e.g. 'bedrock', 'rds')."},
                    "region": {"type": "string", "description": "The AWS region (e.g. 'us-east-1')."}
                },
                "required": ["service", "region"]
            }
        }
    }
]


# --- 4. API ENDPOINTS & LOGIC ---

class QuestionRequest(BaseModel):
    question: str

@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check(response: Response):
    """SRE Live/Ready/Startup Diagnostic probe endpoint."""
    try:
        # 1. Test database connection availability
        conn = await asyncpg.connect(
            host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD, timeout=3
        )
        await conn.close()
        
        # 2. Test Embedding Model is in memory
        _ = embedding_model.encode("healthcheck")
        
        return {"status": "healthy", "database": "connected", "embeddings_engine": "ready"}
    except Exception as e:
        logger.critical(f"Health check failed: {str(e)}")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "unhealthy", "reason": str(e)}

@app.post("/ask")
async def process_question(request: QuestionRequest):
    """Agent Routing Core Endpoint"""
    try:
        messages = [
            {
                "role": "system", 
                "content": (
                    "You are a Virtual Site Reliability Engineer (SRE) and an advanced AIOps Agent. "
                    "Your goal is to diagnose incidents using observability tools and suggest mitigations based on the internal runbook.\n"
                    "STEPS:\n"
                    "1. When diagnosing an incident, you have a variety of tools. ALWAYS query Prometheus metrics ('query_prometheus_metrics') and application logs ('query_loki_logs').\n"
                    "2. If the user mentions connection limits, deployment bugs, or recent changes, use 'query_git_history' to correlate the error with recent GitHub commits.\n"
                    "3. If the user mentions external API failures or timeouts (like Bedrock or AWS), use 'query_aws_health' to check for AWS outages.\n"
                    "4. You MUST use the tool 'search_sre_manual' to check if there is a documented runbook for the error.\n"
                    "5. You MUST respond in the exact same language as the user's question (e.g., if the question is in English, respond in English; if in Portuguese, respond in Portuguese).\n"
                    "6. Depending on the detected language, you MUST strictly use the corresponding format:\n"
                    "   - If responding in English: 'I noticed in chart X that your metric was like this, associated it with logs Y, and found a documentation about this in our database. Joining all the information, the diagnosis is this: [diagnosis], and to resolve it we need [solution]. Can I apply the correction for you or do you wish to do it manually?'\n"
                    "   - If responding in Portuguese: 'Notei no gráfico X que a sua métrica estava dessa forma, associei com os logs Y e achei uma documentação sobre isso no nosso banco de dados. Unindo todas as informações, o diagnóstico é esse: [diagnostico], e para resolver precisamos de [solucao]. Posso aplicar a correção para você ou deseja fazer manualmente?'\n\n"
                    "CRITICAL: When calling tools, you MUST use valid JSON arguments. Do not mix languages (e.g., if the user asked in English, do not output any Portuguese text in your response)."
                )
            },
            {"role": "user", "content": request.question}
        ]

        # Step 1: Model evaluates the input query
        response = await asyncio.to_thread(
            groq_client.chat.completions.create,
            model="llama-3.3-70b-versatile",
            messages=messages,
            tools=tools_schema,
            tool_choice="auto",
            temperature=0.1
        )

        response_message = response.choices[0].message
        messages.append(response_message)

        if response_message.tool_calls:
            for tool_call in response_message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                # Dynamic Tool Routing Execution
                function_response = await execute_tool(function_name, function_args)
                
                messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": function_response,
                })
            
            # Step 2: Generation based on retrieved vector information
            final_response = await asyncio.to_thread(
                groq_client.chat.completions.create,
                model="llama-3.3-70b-versatile",
                messages=messages,
                temperature=0.1
            )
            final_answer = final_response.choices[0].message.content
            tool_used = True
            
            # FinOps Ingestion Logs
            if hasattr(final_response, 'usage') and final_response.usage:
                used_tokens = final_response.usage.total_tokens
                estimated_cost = (used_tokens / 1000) * 0.0007 
                print(f"[FinOps] Tokens consumed: {used_tokens}", flush=True)
                print(f"[FinOps] Estimated cost: ${estimated_cost:.6f}", flush=True)
        else:
            final_answer = response_message.content
            tool_used = False

        return {"question": request.question, "tool_used": tool_used, "answer": final_answer}

    except Exception as e:
        logger.error(f"Internal processing error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Error: {str(e)}")

@app.post("/upload_document")
async def update_knowledge_base(file: UploadFile = File(...)):
    """Dynamic Knowledge Base Ingestion Pipeline via database vectorization"""
    try:
        content = await file.read()
        text = content.decode("utf-8")
        chunks = [chunk.strip() for chunk in text.split("\n\n") if chunk.strip()]
        
        conn = await asyncpg.connect(
            host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD
        )
        try:
            for chunk in chunks:
                enriched_chunk = f"[Context: File {file.filename}] {chunk}"
                
                # Generate embeddings locally inside the API engine
                vector = embedding_model.encode(enriched_chunk).tolist()
                
                # Insert the document chunk alongside its vector mathematical array
                await conn.execute("""
                    INSERT INTO sre_knowledge_base (filename, chunk_content, embedding)
                    VALUES ($1, $2, $3::vector);
                """, file.filename, enriched_chunk, str(vector))
                
            return {
                "status": "success", 
                "message": f"File {file.filename} successfully chunked, vectorized and stored in RDS PostgreSQL.",
                "processed_chunks": len(chunks)
            }
        finally:
            await conn.close()
    except Exception as e:
        logger.error(f"Ingestion pipeline failure: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")