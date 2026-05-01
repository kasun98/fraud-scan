# Fraud Detection System — Full Startup Runbook

## 1 — Start Minikube

```powershell
minikube start --cpus=6 --memory=10240 --disk-size=40g --driver=docker
```

Verify:

```powershell
minikube status
```

---

## 2 — Create namespaces

```powershell
kubectl create namespace kafka
kubectl create namespace fraud-detection
kubectl create namespace observability
```

---

## 3 — Install Strimzi operator

```powershell
helm repo add strimzi https://strimzi.io/charts/
helm repo update

helm install strimzi-operator strimzi/strimzi-kafka-operator --namespace kafka --set watchNamespaces="{fraud-detection,kafka,observability}"

# Wait for operator to be ready
kubectl rollout status deployment/strimzi-cluster-operator -n kafka --timeout=120s
```

---

## 4 — Deploy Kafka cluster

```powershell
kubectl apply -f k8s/kafka/cluster.yaml
```

Watch until all pods are Running (takes 2–4 min):

```powershell
kubectl get pods -n kafka -w
```

Wait for these three:

```
fraud-kafka-combined-0              1/1   Running
fraud-kafka-entity-operator-xxx     2/2   Running
strimzi-cluster-operator-xxx        1/1   Running
```

Verify Kafka is Ready:

```powershell
kubectl get kafka -n kafka
# READY should be True, KAFKA VERSION should be 4.0.0
```

---

## 5 — Create Kafka topics

```powershell
kubectl apply -f k8s/kafka/topics.yaml

# Verify all 4 topics are Ready
kubectl get kafkatopics -n kafka
```

Expected:

```
NAME                  CLUSTER       PARTITIONS   REPLICATION FACTOR   READY
fraud-alerts          fraud-kafka   3            1                    True
fraud-decisions       fraud-kafka   3            1                    True
transactions-raw      fraud-kafka   3            1                    True
transactions-scored   fraud-kafka   3            1                    True
```

---

## 6 — Install Redis and Postgres

```powershell
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update

# Redis
helm install redis bitnami/redis --namespace fraud-detection --set auth.enabled=false --set master.persistence.enabled=false --set replica.replicaCount=0

# Postgres
helm install postgres bitnami/postgresql --namespace fraud-detection --set auth.postgresPassword=localdev --set auth.database=fraud_db --set primary.persistence.enabled=false

# Wait for both
kubectl rollout status statefulset/redis-master        -n fraud-detection --timeout=120s
kubectl rollout status statefulset/postgres-postgresql -n fraud-detection --timeout=120s
```

---

## 7 — Apply database schema

Apply the schema:

```powershell
cat k8s/postgres/schema.sql | kubectl exec -i svc/postgres-postgresql -n fraud-detection -- sh -c 'PGPASSWORD="localdev" psql -U postgres -d fraud_db'
```

Verify tables exist:

```powershell
kubectl exec -i svc/postgres-postgresql -n fraud-detection -- sh -c "PGPASSWORD='localdev' psql -U postgres -d fraud_db -c '\dt'"
# Should show: fraud_decisions, case_reviews, alert_log
```

---

## 8 — Create Kubernetes secret

```powershell
kubectl apply -f k8s/secrets.yaml
```

---

## 9 — Build all Docker images

```powershell
# Point Docker to Minikube daemon
& minikube -p minikube docker-env | Invoke-Expression

# Build all services
docker build -t transaction-simulator:latest services/transaction-simulator/
# docker build -t transaction-api:latest       services/transaction-api/
docker build -t feature-engineering:latest   services/feature-engineering/
docker build -t ml-scoring:latest            services/ml-scoring/
docker build -t decision-aggregator:latest   services/decision-aggregator/
docker build -t case-management-api:latest   services/case-management-api/
docker build -t case-management-ui:latest    services/case-management-ui/
```

---

## 10 — Deploy all services via Helm

```powershell
# Lint all charts first
helm lint helm/charts/transaction-simulator
# helm lint helm/charts/transaction-api
helm lint helm/charts/feature-engineering
helm lint helm/charts/ml-scoring
helm lint helm/charts/decision-aggregator
helm lint helm/charts/case-management-api
helm lint helm/charts/case-management-ui

# Deploy in pipeline order
helm upgrade --install transaction-simulator helm/charts/transaction-simulator --namespace fraud-detection

# helm upgrade --install transaction-api helm/charts/transaction-api --namespace fraud-detection

helm upgrade --install feature-engineering helm/charts/feature-engineering --namespace fraud-detection

helm upgrade --install ml-scoring helm/charts/ml-scoring --namespace fraud-detection

helm upgrade --install decision-aggregator helm/charts/decision-aggregator --namespace fraud-detection

helm upgrade --install case-management-api helm/charts/case-management-api --namespace fraud-detection

helm upgrade --install case-management-ui helm/charts/case-management-ui --namespace fraud-detection

helm upgrade --install prometheus prometheus-community/kube-prometheus-stack --namespace observability -f prometheus/values.yaml --timeout 10m
```

---

## 11 — Verify all pods are running

```powershell
kubectl get pods -n fraud-detection
kubectl get pods -n kafka
```

Expected output:

```
NAMESPACE        NAME                                READY   STATUS
fraud-detection  c-xxx             1/1     Running
fraud-detection  case-management-ui-xxx              1/1     Running
fraud-detection  decision-aggregator-xxx             1/1     Running
fraud-detection  feature-engineering-xxx             1/1     Running
fraud-detection  ml-scoring-xxx                      1/1     Running
fraud-detection  postgres-postgresql-0               1/1     Running
fraud-detection  redis-master-0                      1/1     Running
fraud-detection  transaction-api-xxx                 1/1     Running
fraud-detection  transaction-simulator-xxx           0/1     Running

kafka            fraud-kafka-combined-0              1/1     Running
kafka            fraud-kafka-entity-operator-xxx     3/3     Running
kafka            strimzi-cluster-operator-xxx        1/1     Running
```

If any pod is in `CrashLoopBackOff`, check its logs:

```powershell
kubectl logs deployment/<service-name> -n fraud-detection --tail=30
```

---

## 12 — Start the simulator to generate data

```powershell
kubectl scale deployment/transaction-simulator -n fraud-detection --replicas=1
```

Watch the pipeline flowing (open separate terminals for each):

```powershell
# Transactions being produced
kubectl logs -f deployment/transaction-simulator -n fraud-detection

# Features being computed into Redis
kubectl logs -f deployment/feature-engineering -n fraud-detection

# Decisions being scored by ML + rules engine
kubectl logs -f deployment/ml-scoring -n fraud-detection

# Decisions being saved to Postgres
kubectl logs -f deployment/decision-aggregator -n fraud-detection
```

---

## 13 — Open the UI

```powershell
kubectl port-forward svc/case-management-ui 3000:80 -n fraud-detection
```

Open your browser at:

```
http://localhost:3000
```

Let it run for 30–60 seconds so data populates. You will see:

- **Dashboard** — live transaction table with decision badges, score bars, and animated stat cards
- **Analytics** — decision split pie chart, bar chart, latency metrics (avg / p95 / min / max)
- **Case detail** — click any row to review a transaction and submit analyst feedback

---

## 14 — Optional port-forwards for direct API access

```powershell
# Case management API (REST)
kubectl port-forward svc/case-management-api 8002:8002 -n fraud-detection
# → http://localhost:8002/docs

# ML scoring API
kubectl port-forward svc/ml-scoring 8001:8001 -n fraud-detection
# → http://localhost:8001/docs

# Transaction ingestion API
# kubectl port-forward svc/transaction-api 8000:8000 -n fraud-detection
# → http://localhost:8000/docs

# Postgres direct access
kubectl port-forward svc/postgres-postgresql 5432:5432 -n fraud-detection
```

---

## 15 — Simulator control

```powershell
# Stop data generation
kubectl scale deployment/transaction-simulator -n fraud-detection --replicas=0

# Resume data generation
kubectl scale deployment/transaction-simulator -n fraud-detection --replicas=1
```

---

## 16 — Scaling Testing

```powershell
# Install KEDA
helm repo add kedacore https://kedacore.github.io/charts
helm repo update
helm upgrade --install keda kedacore/keda --namespace keda --create-namespace
kubectl rollout status deployment/keda-operator -n keda --timeout=120s

kubectl get pods -n keda
kubectl apply -f k8s/keda/
kubectl get scaledobject -n fraud-detection

# Test
scripts/scaling-test.ps1

# Monitor (New Terminal)
scripts/monitor-pods.ps1
```

---

## Quick system status check

Run this anytime to see the full state:

```powershell
Write-Host "`n=== Minikube ===" -ForegroundColor Cyan
minikube status

Write-Host "`n=== Kafka ===" -ForegroundColor Cyan
kubectl get kafka -n kafka

Write-Host "`n=== Topics ===" -ForegroundColor Cyan
kubectl get kafkatopics -n kafka

Write-Host "`n=== Fraud Detection Pods ===" -ForegroundColor Cyan
kubectl get pods -n fraud-detection

Write-Host "`n=== Kafka Pods ===" -ForegroundColor Cyan
kubectl get pods -n kafka

Write-Host "`n=== Helm Releases ===" -ForegroundColor Cyan
helm list -n fraud-detection

Write-Host "`n=== Port forwards needed ===" -ForegroundColor Yellow
Write-Host "kubectl port-forward svc/case-management-ui  3000:80   -n fraud-detection"
Write-Host "kubectl port-forward svc/case-management-api 8002:8002 -n fraud-detection"
Write-Host "kubectl port-forward svc/ml-scoring          8001:8001 -n fraud-detection"
# Write-Host "kubectl port-forward svc/transaction-api     8000:8000 -n fraud-detection"
```

---

## Data pipeline flow

```
transaction-simulator
        │
        ▼ (transactions-raw)
feature-engineering ──► Redis (user feature cache)
        │
        ▼ (transactions-scored)
ml-scoring (XGBoost + rules engine)
        │
        ▼ (fraud-decisions)
decision-aggregator ──► Postgres (fraud_decisions table)
        │
        ▼ (fraud-alerts)
case-management-api ◄── case-management-ui (http://localhost:3000)
```

---

## Troubleshooting reference

| Problem | Command |
|---|---|
| Pod in CrashLoopBackOff | `kubectl logs deployment/<name> -n fraud-detection --tail=50` |
| Kafka not Ready | `kubectl logs -n kafka deployment/strimzi-cluster-operator --tail=40` |
| No data in UI | `kubectl logs deployment/decision-aggregator -n fraud-detection --tail=20` |
| Postgres connection error | `kubectl get secret fraud-secrets -n fraud-detection` |
| Image not found | `& minikube -p minikube docker-env \| Invoke-Expression` then rebuild |
| Strimzi version mismatch | `helm list -n kafka` — must be 0.51.0 with Kafka 4.0.0 |
