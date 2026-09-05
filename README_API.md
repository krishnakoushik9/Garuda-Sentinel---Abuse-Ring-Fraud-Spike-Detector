# PS2 Fraud Intelligence Platform - API Documentation

Base URL: `http://localhost:8000/api/v1`

## Dashboard
### Get Summary
```bash
curl -X GET http://localhost:8000/api/v1/dashboard/summary
```

## Transactions
### List Transactions
```bash
curl -X GET "http://localhost:8000/api/v1/transactions?limit=10&risk_tier=suspicious"
```

### Get Stats
```bash
curl -X GET http://localhost:8000/api/v1/transactions/stats
```

## Accounts
### List Accounts
```bash
curl -X GET "http://localhost:8000/api/v1/accounts?limit=5"
```

### Get Profile
```bash
curl -X GET http://localhost:8000/api/v1/accounts/ACC000001
```

### Get Graph Neighborhood (D3 JSON)
```bash
curl -X GET http://localhost:8000/api/v1/accounts/ACC000001/graph
```

### Flag Account
```bash
curl -X POST http://localhost:8000/api/v1/accounts/ACC000001/flag
```

## Investigations (LangGraph Agents)
### Start Investigation
```bash
curl -X POST "http://localhost:8000/api/v1/investigate?txn_id=TXN000000000001&account_id=ACC000001"
```

### Get Result
```bash
curl -X GET http://localhost:8000/api/v1/investigate/{investigation_id}
```

## Alerts
### List Alerts
```bash
curl -X GET http://localhost:8000/api/v1/alerts
```

### Stream Alerts (SSE)
```bash
curl -N http://localhost:8000/api/v1/alerts/stream
```

## Graph Analytics
### Fraud Rings
```bash
curl -X GET http://localhost:8000/api/v1/graph/fraud-rings
```

### Community Members
```bash
curl -X GET http://localhost:8000/api/v1/graph/community/123
```

### Graph Stats
```bash
curl -X GET http://localhost:8000/api/v1/graph/stats
```
