# Useful PromQL Queries for ACM Observability

## Cluster Health

### CPU Usage per Cluster
```promql
sum(rate(node_cpu_seconds_total{mode!="idle"}[5m])) by (cluster)
```

### Memory Usage per Cluster
```promql
sum(node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) by (cluster)
```

## ACM Components

### Observability Addon Status
```promql
acm_addon_status{addon="observability-controller"}
```
