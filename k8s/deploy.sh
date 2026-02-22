#!/bin/bash

set -e

NAMESPACE="contract-guard"
IMAGE_NAME="contract-guard"
TAG=${1:-latest}

echo "Deploying ContractGuardAgent to Kubernetes..."

# Build Docker image
echo "Building Docker image..."
docker build -t ${IMAGE_NAME}:${TAG} .

# Apply Kubernetes resources
echo "Creating namespace..."
kubectl apply -f k8s/namespace.yaml

echo "Applying ConfigMap..."
kubectl apply -f k8s/configmap.yaml

echo "Applying PVC..."
kubectl apply -f k8s/pvc.yaml

echo "Deploying Ollama..."
kubectl apply -f k8s/ollama-deployment.yaml
kubectl apply -f k8s/ollama-service.yaml

echo "Deploying ContractGuard..."
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml

echo "Applying Ingress..."
kubectl apply -f k8s/ingress.yaml

# Wait for deployments
echo "Waiting for deployments..."
kubectl wait --for=condition=available --timeout=300s deployment/ollama -n ${NAMESPACE}
kubectl wait --for=condition=available --timeout=300s deployment/contract-guard -n ${NAMESPACE}

# Pull model in Ollama
echo "Pulling llama3.2 model in Ollama..."
kubectl exec -n ${NAMESPACE} deploy/ollama -- ollama pull llama3.2

echo "Deployment complete!"
echo "Access the application at: http://contract-guard.local"
echo "Check status: kubectl get pods -n ${NAMESPACE}"
