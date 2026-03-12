# Asesor Virtual — Banco Caja Social

Chatbot de IA para el Banco Caja Social con Azure OpenAI GPT-4o-mini, voz (Azure Speech TTS/STT), interfaz web y despliegue en AKS.

## Arquitectura

```
Usuario (Chrome) → HTTPS → NGINX Ingress (LoadBalancer)
    → ClusterIP → Pod Flask/Gunicorn
        → Azure OpenAI (GPT-4o-mini)
        → Azure Speech (TTS: es-CO-SalomeNeural / STT: es-CO)
    ← Respuesta texto + audio
```

**Servicios Azure utilizados:**
- Azure OpenAI (GPT-4o-mini)
- Azure Speech Services (TTS + STT)
- Azure Kubernetes Service (AKS) — 1 nodo Standard_D2als_v7
- Azure Container Registry (ACR) — Basic
- Azure Key Vault — secretos
- cert-manager + Let's Encrypt — TLS automático
- (Opcional) Log Analytics + Azure Monitor Workbook — dashboard de auditoría

## Requisitos Previos

- Python 3.10+
- Azure CLI (`az`) autenticado
- kubectl y Helm
- Suscripción Azure activa con permisos de Contributor

## Variables de Entorno

Copiar `.env.example` a `.env` y completar:

```
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_KEY=your-key
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o-mini
AZURE_OPENAI_API_VERSION=2024-10-21
AZURE_SPEECH_KEY=your-speech-key
AZURE_SPEECH_REGION=swedencentral
```

## Desarrollo Local

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Editar .env con tus claves Azure
python web_server.py
# → http://localhost:5000
```

## Despliegue en Azure (paso a paso)

### Paso 0 — Login

```bash
az login
az account set --subscription "Azure subscription 1"
```

### Paso 1 — Resource Group

```bash
az group create --name rg-bcs-bot --location eastus2
```

### Paso 2 — Container Registry (ACR)

```bash
az acr create --resource-group rg-bcs-bot --name acrbcsbot --sku Basic
```

### Paso 3 — Key Vault + Secretos

```bash
az keyvault create \
    --resource-group rg-bcs-bot \
    --name kv-bcsbot \
    --location eastus2 \
    --enable-rbac-authorization false

# Sincronizar secretos desde .env
while IFS='=' read -r key value; do
    [[ "$key" =~ ^#.*$ || -z "$key" ]] && continue
    secret_name=$(echo "$key" | tr '_' '-')
    az keyvault secret set --vault-name kv-bcsbot --name "$secret_name" --value "$value"
done < .env
```

### Paso 4 — Build de imagen Docker

```bash
az acr login --name acrbcsbot
az acr build --registry acrbcsbot --image bcs-bot:latest .
```

### Paso 5 — AKS Cluster

```bash
az aks create \
    --resource-group rg-bcs-bot \
    --name aks-bcs-bot \
    --node-count 1 \
    --node-vm-size Standard_D2als_v7 \
    --attach-acr acrbcsbot \
    --enable-addons azure-keyvault-secrets-provider \
    --generate-ssh-keys

az aks get-credentials --resource-group rg-bcs-bot --name aks-bcs-bot --overwrite-existing
```

### Paso 6 — Acceso Key Vault → AKS

```bash
CLIENT_ID=$(az aks show \
    --resource-group rg-bcs-bot --name aks-bcs-bot \
    --query "addonProfiles.azureKeyvaultSecretsProvider.identity.clientId" -o tsv)

TENANT_ID=$(az account show --query tenantId -o tsv)

az keyvault set-policy \
    --name kv-bcsbot \
    --spn $CLIENT_ID \
    --secret-permissions get list
```

### Paso 7 — NGINX Ingress Controller

```bash
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update

helm install ingress-nginx ingress-nginx/ingress-nginx \
    --create-namespace \
    --namespace ingress-nginx \
    --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-dns-label-name"=bcs-bot \
    --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-load-balancer-health-probe-request-path"=/healthz

# Esperar IP pública (~2 min)
kubectl get svc ingress-nginx-controller -n ingress-nginx -w
```

### Paso 8 — cert-manager (TLS / HTTPS)

```bash
helm repo add jetstack https://charts.jetstack.io
helm repo update

helm install cert-manager jetstack/cert-manager \
    --namespace cert-manager \
    --create-namespace \
    --set crds.enabled=true

kubectl wait --for=condition=available deployment/cert-manager -n cert-manager --timeout=120s
kubectl wait --for=condition=available deployment/cert-manager-webhook -n cert-manager --timeout=120s
```

### Paso 9 — Aplicar manifiestos Kubernetes

Reemplazar placeholders y aplicar:

```bash
kubectl apply -f k8s/namespace.yaml

# SecretProviderClass (reemplazar placeholders)
sed "s/__KEYVAULT_NAME__/kv-bcsbot/g; s/__TENANT_ID__/$TENANT_ID/g; s/__CLIENT_ID__/$CLIENT_ID/g" \
    k8s/secret-provider-class.yaml | kubectl apply -f -

# ClusterIssuer (reemplazar email)
sed "s/__ACME_EMAIL__/jairoandreszabala@hotmail.com/g" \
    k8s/cluster-issuer.yaml | kubectl apply -f -

kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml

# Esperar
kubectl rollout status deployment/bcs-bot -n bcs-bot --timeout=120s
```

### Paso 10 — Verificar

```bash
kubectl get pods -n bcs-bot
kubectl get certificate -n bcs-bot
echo "https://bcs-bot.eastus2.cloudapp.azure.com"
```

## Despliegue rápido (Windows PowerShell)

```powershell
# Automatiza todos los pasos anteriores
.\deploy.ps1
```

## Dashboard de Auditoría (opcional)

```bash
python docs/deploy_dashboard_azure.py
```

## Detener / Iniciar AKS (ahorro de costos)

```bash
# Detener (~$43/mes ahorrados)
az aks stop --resource-group rg-bcs-bot --name aks-bcs-bot

# Iniciar
az aks start --resource-group rg-bcs-bot --name aks-bcs-bot
az aks get-credentials --resource-group rg-bcs-bot --name aks-bcs-bot --overwrite-existing
```

## Eliminar TODO y volver a $0

```bash
az group delete --name rg-bcs-bot --yes --no-wait
```

Para volver a desplegar, seguir desde el Paso 0.

## Estructura del Proyecto

```
banco_caja_social_bot/
├── app/
│   ├── bot.py                  # Azure OpenAI integration
│   ├── knowledge_base.py       # Conocimiento del banco
│   └── voice.py                # TTS/STT con Azure Speech
├── web/
│   ├── static/{css,js,img}/    # Frontend
│   └── templates/index.html
├── k8s/                        # Manifiestos Kubernetes
│   ├── namespace.yaml
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── ingress.yaml
│   ├── secret-provider-class.yaml
│   └── cluster-issuer.yaml
├── docs/                       # Auditoría y diagramas
├── web_server.py               # Flask server
├── main.py                     # CLI entry point
├── Dockerfile
├── deploy.ps1                  # Despliegue automatizado
├── requirements.txt
└── .env.example
```

## Costos Aproximados

| Recurso | Costo/mes | Notas |
|---------|-----------|-------|
| AKS (1 nodo D2als_v7) | ~$43 | Se puede detener |
| ACR Basic | ~$5 | Imágenes Docker |
| Key Vault | ~$0.03 | Mínimo |
| Azure OpenAI | ~$0.60/1M tokens | Pay per use |
| Azure Speech | ~$1/hr audio | Pay per use |
| **Total activo** | **~$50/mes** | Sin contar IA |
| **Total detenido** | **~$5/mes** | Solo ACR + KV |
