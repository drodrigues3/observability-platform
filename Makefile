# ============================================================================
# Observability Platform — Makefile
# ============================================================================
# Usage:
#   make install          Install all Python dependencies (poetry)
#   make test             Run all unit tests
#   make test-cov         Run all tests with coverage report
#   make lint             Run ruff + mypy on all apps
#   make build            Build Docker images for all apps
#   make cluster          Create kind cluster + namespaces
#   make deploy           Deploy full stack (Helm)
#   make run              Full setup: cluster + build + deploy
#   make port-forward     Port-forward Grafana, Prometheus, metrics-bridge
#   make smoke-test       Run end-to-end smoke tests
#   make clean            Tear down everything (Helm releases, kind cluster, images)
#   make help             Show this help
# ============================================================================

.DEFAULT_GOAL := help
SHELL := /bin/bash

# ---------------------------------------------------------------------------
# Variables
# ---------------------------------------------------------------------------
CLUSTER_NAME     := observability
APPS             := workload-simulator stream-processor metrics-bridge
IMAGE_TAG        := local
HELM_RELEASE     := obs
HELM_CHART       := ./helm/observability-platform
MONITORING_NS    := monitoring
OBSERVABILITY_NS := observability

# ---------------------------------------------------------------------------
# Install
# ---------------------------------------------------------------------------
.PHONY: install
install: ## Install all Python app dependencies via Poetry
	@echo "=== Installing dependencies for all apps ==="
	@for app in $(APPS); do \
		echo "--- $$app ---"; \
		cd apps/$$app && poetry install && cd ../..; \
	done
	@echo "=== All dependencies installed ==="

# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------
.PHONY: test
test: ## Run unit tests for all apps
	@echo "=== Running tests ==="
	@failed=0; \
	for app in $(APPS); do \
		echo ""; \
		echo "--- Testing $$app ---"; \
		cd apps/$$app && poetry run pytest tests/ -v --tb=short; \
		if [ $$? -ne 0 ]; then failed=1; fi; \
		cd ../..; \
	done; \
	if [ $$failed -ne 0 ]; then \
		echo ""; \
		echo "=== SOME TESTS FAILED ==="; \
		exit 1; \
	fi; \
	echo ""; \
	echo "=== ALL TESTS PASSED ==="

.PHONY: test-cov
test-cov: ## Run tests with coverage report
	@echo "=== Running tests with coverage ==="
	@for app in $(APPS); do \
		echo ""; \
		echo "--- $$app coverage ---"; \
		cd apps/$$app && poetry run pytest tests/ -v --tb=short \
			--cov --cov-report=term-missing --cov-fail-under=60; \
		cd ../..; \
	done

# ---------------------------------------------------------------------------
# Lint
# ---------------------------------------------------------------------------
.PHONY: lint
lint: ## Run ruff and mypy on all apps
	@echo "=== Linting all apps ==="
	@for app in $(APPS); do \
		echo ""; \
		echo "--- Linting $$app ---"; \
		cd apps/$$app && poetry run ruff check . && poetry run mypy . --ignore-missing-imports; \
		cd ../..; \
	done
	@echo "=== Lint complete ==="

# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------
.PHONY: build
build: ## Build Docker images for all apps
	@echo "=== Building Docker images ==="
	@for app in $(APPS); do \
		echo "--- Building $$app ---"; \
		docker build -t $$app:$(IMAGE_TAG) ./apps/$$app; \
	done
	@echo "=== All images built ==="

# ---------------------------------------------------------------------------
# Cluster
# ---------------------------------------------------------------------------
.PHONY: cluster
cluster: ## Create kind cluster and apply namespaces + RBAC
	@echo "=== Creating kind cluster ==="
	kind create cluster --name $(CLUSTER_NAME) --config kind-config.yaml
	kubectl apply -f k8s/namespaces.yaml
	kubectl apply -f k8s/rbac.yaml
	kubectl apply -f k8s/network-policies.yaml
	@echo "=== Cluster ready ==="

# ---------------------------------------------------------------------------
# Deploy
# ---------------------------------------------------------------------------
.PHONY: helm-deps
helm-deps: ## Update Helm chart dependencies
	@echo "=== Updating Helm dependencies ==="
	helm repo add bitnami https://charts.bitnami.com/bitnami 2>/dev/null || true
	helm repo add prometheus-community https://prometheus-community.github.io/helm-charts 2>/dev/null || true
	helm repo update
	cd $(HELM_CHART) && helm dependency update
	@echo "=== Helm dependencies updated ==="

.PHONY: load-images
load-images: ## Load Docker images into kind cluster
	@echo "=== Loading images into kind ==="
	@for app in $(APPS); do \
		kind load docker-image $$app:$(IMAGE_TAG) --name $(CLUSTER_NAME); \
	done
	@echo "=== Images loaded ==="

.PHONY: deploy
deploy: helm-deps load-images ## Deploy full stack via Helm (assumes cluster + images exist)
	@echo "=== Deploying observability platform ==="
	helm upgrade --install $(HELM_RELEASE) $(HELM_CHART) \
		-f $(HELM_CHART)/values-dev.yaml \
		-n $(MONITORING_NS) --create-namespace --wait --timeout 10m
	@echo "--- Deploying application workloads ---"
	helm upgrade --install workload-sim ./helm/workload-simulator \
		-n $(OBSERVABILITY_NS) --create-namespace --wait
	helm upgrade --install stream-proc ./helm/stream-processor \
		-n $(OBSERVABILITY_NS) --wait
	helm upgrade --install metrics-br ./helm/metrics-bridge \
		-n $(OBSERVABILITY_NS) --wait
	@echo "=== Deployment complete ==="

# ---------------------------------------------------------------------------
# Run (full setup from zero)
# ---------------------------------------------------------------------------
.PHONY: run
run: cluster build deploy ## Full setup: create cluster, build images, deploy everything
	@echo ""
	@echo "=== Platform is running ==="
	@echo "Run 'make port-forward' to access Grafana and Prometheus"

# ---------------------------------------------------------------------------
# Port-forward
# ---------------------------------------------------------------------------
.PHONY: port-forward
port-forward: ## Port-forward Grafana (3000), Prometheus (9090), metrics-bridge (8080)
	@echo "=== Starting port-forwards ==="
	@echo "Grafana:        http://localhost:3000  (admin / observability123)"
	@echo "Prometheus:     http://localhost:9090"
	@echo "Metrics Bridge: http://localhost:8080/metrics"
	@echo ""
	@echo "Press Ctrl+C to stop all port-forwards"
	kubectl port-forward svc/$(HELM_RELEASE)-grafana 3000:80 -n $(MONITORING_NS) &
	kubectl port-forward svc/$(HELM_RELEASE)-kube-prometheus-stack-prometheus 9090:9090 -n $(MONITORING_NS) &
	kubectl port-forward svc/metrics-bridge 8080:8080 -n $(OBSERVABILITY_NS) &
	wait

# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------
.PHONY: smoke-test
smoke-test: ## Run end-to-end smoke tests (requires port-forward)
	@echo "=== Running smoke tests ==="
	python tests/smoke_test.py

# ---------------------------------------------------------------------------
# Load test
# ---------------------------------------------------------------------------
.PHONY: load-test
load-test: ## Run load test (spike to 100 RPS for 2 min)
	python scripts/load_test.py --target-rps 100 --error-rate 0.1 --duration 120

# ---------------------------------------------------------------------------
# Clean
# ---------------------------------------------------------------------------
.PHONY: clean
clean: ## Tear down Helm releases, kind cluster, and local Docker images
	@echo "=== Cleaning up ==="
	-helm uninstall metrics-br -n $(OBSERVABILITY_NS) 2>/dev/null
	-helm uninstall stream-proc -n $(OBSERVABILITY_NS) 2>/dev/null
	-helm uninstall workload-sim -n $(OBSERVABILITY_NS) 2>/dev/null
	-helm uninstall $(HELM_RELEASE) -n $(MONITORING_NS) 2>/dev/null
	-kind delete cluster --name $(CLUSTER_NAME) 2>/dev/null
	@for app in $(APPS); do \
		docker rmi $$app:$(IMAGE_TAG) 2>/dev/null || true; \
	done
	@echo "=== Clean complete ==="

.PHONY: clean-images
clean-images: ## Remove local Docker images only
	@for app in $(APPS); do \
		docker rmi $$app:$(IMAGE_TAG) 2>/dev/null || true; \
	done
	@echo "=== Images removed ==="

# ---------------------------------------------------------------------------
# Helm lint
# ---------------------------------------------------------------------------
.PHONY: lint-helm
lint-helm: ## Lint all Helm charts
	@echo "=== Linting Helm charts ==="
	helm lint helm/workload-simulator/
	helm lint helm/stream-processor/
	helm lint helm/metrics-bridge/
	helm lint $(HELM_CHART) --set kube-prometheus-stack.enabled=false --set kafka.enabled=false
	@echo "=== Helm lint passed ==="

# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------
.PHONY: help
help: ## Show this help
	@echo "Observability Platform — Available targets:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'
	@echo ""
