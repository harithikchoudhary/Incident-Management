# AI-Powered Incident Management Platform

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Streamlit Frontend                             │
├─────────────────────────────────────────────────────────────────────┤
│                         FastAPI Backend                               │
├──────────┬──────────┬──────────┬──────────┬─────────────────────────┤
│  API     │  Agents  │ Services │  Graph   │   Tools                  │
│  Layer   │          │          │(LangGraph)│                          │
├──────────┼──────────┼──────────┼──────────┼─────────────────────────┤
│          │          │          │          │                           │
│ incidents│ extractor│ llm      │ incident │  search_incidents        │
│ ingestion│ analyzer │ embedding│ _graph   │  get_incident            │
│ search   │ retriever│ retrieval│          │  get_source_conversation │
│          │ resolut. │ incident │          │                           │
│          │ supervis.│ ingestion│          │                           │
├──────────┴──────────┴──────────┴──────────┴─────────────────────────┤
│  Repository Layer (PostgreSQL)  │  FAISS Vector Index                │
├─────────────────────────────────┴───────────────────────────────────┤
│         ChatSource Interface (MockChatSource / GoogleChatSource)      │
└─────────────────────────────────────────────────────────────────────┘
```

## Components

| Component | Purpose |
|-----------|---------|
| API Layer | FastAPI endpoints for incidents, ingestion, search, analysis |
| Agents | LLM-powered extraction, analysis, retrieval, resolution |
| Services | Business logic, LLM/embedding abstraction, retrieval |
| Graph | LangGraph workflow orchestrating the analysis pipeline |
| Tools | Tool interface for agents to access data |
| Repository | Database access layer (PostgreSQL) |
| ChatSource | Pluggable interface for chat data sources |

## Data Flow

### Ingestion
```
Mock JSON → ChatSource → Thread Grouping → Incident Extractor → 
Validation → Repository (PostgreSQL) → Embedding → FAISS Index
```

### Analysis
```
New Incident → Analyzer → Retriever → Evidence Retriever → 
Resolution Agent → Response Formatter → API Response
```

## Setup

### Prerequisites
- Python 3.10+
- PostgreSQL 14+
- AWS credentials (for Bedrock LLM) or use fallback mode

### Environment Variables

```bash
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/incident_management
AWS_REGION=us-east-1
AWS_BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
AWS_BEDROCK_EMBEDDING_MODEL_ID=amazon.titan-embed-text-v1
FAISS_INDEX_PATH=./data/faiss_index
MOCK_CHAT_PATH=./data/original_incident_data.json
```

### Database Setup

```sql
CREATE DATABASE incident_management;
```

Tables are auto-created on first run via SQLAlchemy.

## How to Run

### Backend

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env  # Edit with your settings
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
pip install -r requirements.txt
streamlit run frontend\app.py --server.port 8501
```

## How to Ingest Mock Data

```bash
curl -X POST http://localhost:8000/api/ingestion/mock-chat
```

Or use the "Data Ingestion" page in the UI.

## How to Analyze a New Incident

```bash
curl -X POST http://localhost:8000/api/incidents/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Payment API returning 500 errors. Logs show database connection pool exhausted.",
    "application": "Payment API",
    "environment": "PROD"
  }'
```

## Example API Requests

### List incidents
```bash
curl http://localhost:8000/api/incidents
```

### Get specific incident
```bash
curl http://localhost:8000/api/incidents/INC-XXXXXXXX
```

### Search incidents
```bash
curl "http://localhost:8000/api/incidents/search?q=database+connection+pool"
```

### Get conversation
```bash
curl http://localhost:8000/api/incidents/INC-XXXXXXXX/conversation
```

### Health check
```bash
curl http://localhost:8000/api/health
```

## Example Response (Analysis)

```json
{
  "incident_summary": "Payment API returning 500 errors. Logs show database connection pool exhausted.",
  "likely_root_cause": "DB connection pool exhaustion due to increased traffic",
  "confidence": 0.94,
  "confidence_level": "HIGH",
  "matched_incidents": [
    {
      "incident_id": "INC-A1B2C3D4",
      "similarity": 0.94,
      "reason": "Same application: Payment API. Similar root cause pattern: DB connection pool exhaustion"
    }
  ],
  "recommended_resolution": [
    "Increase DB connection pool size",
    "Restart payment-service"
  ],
  "evidence": [
    {
      "incident_id": "INC-A1B2C3D4",
      "source_thread_id": "thread-001",
      "source_message_ids": ["msg-001", "msg-002", "msg-003"]
    }
  ],
  "warnings": [
    "Verify current database connection limits before changing configuration."
  ]
}
```

## Retrieval Algorithm

The hybrid search combines multiple signals with configurable weights:

| Signal | Weight | Description |
|--------|--------|-------------|
| Semantic similarity | 0.5 | FAISS cosine similarity of embeddings |
| Keyword matching | 0.2 | Token overlap between query and incident |
| Error code matching | 0.2 | Exact match on HTTP error codes |
| Application matching | 0.1 | Exact or partial application name match |

Final score = Σ(signal × weight)

Confidence levels:
- **HIGH** (≥ 0.85): Strong historical match found
- **MEDIUM** (0.65 - 0.84): Partial match, verify before applying
- **LOW** (< 0.65): No reliable match, manual investigation needed

## Replacing MockChatSource with Google Chat API

The `ChatSource` interface defines:

```python
class ChatSource(ABC):
    def get_spaces(self) -> List[ChatSpace]: ...
    def get_messages(self, space_id: str) -> List[ChatMessage]: ...
    def get_threads(self, space_id: str) -> List[ChatThread]: ...
```

To integrate Google Chat:

1. Implement `GoogleChatSource(ChatSource)` using the Google Chat API
2. Update the dependency injection to use `GoogleChatSource`
3. No changes needed to agents, services, or API layer

## Future Improvements

- Real Google Chat API integration
- Automated scheduled ingestion
- Slack/Teams integration
- Real-time incident detection
- Feedback loop for resolution accuracy
- Multi-tenant support
- Role-based access control
- Incident timeline visualization
- Auto-generated runbooks
- Integration with PagerDuty/OpsGenie





1. User clicks "Ingest Mock Chat Data" in frontend
   ↓
2. POST /api/ingestion/mock-chat
   ↓
3. MockChatSource reads mock_google_chat.json
   ↓
4. Groups messages by thread_id → ChatThread objects
   ↓
5. For each thread:
   - IncidentExtractor.extract(thread) → uses LLM to parse
   - Creates Incident object
   ↓
6. IncidentService.create_incident(incident):
   - Saves to SQLite: repository.save(incident)
   - Creates embedding: retrieval_service.index_incident(incident)
     → Embeds text → Adds to FAISS index
   ↓
7. Returns success/failure counts








