$RESOURCE_GROUP   = "rg-bcs-bot"
$ACME_EMAIL       = "jairoandreszabala@hotmail.com"
$LOCATION         = "eastus2"
$ACR_NAME         = "acrbcsbot"
$AKS_NAME         = "aks-bcs-bot"
$KV_NAME          = "kv-bcsbot"
$DNS_LABEL        = "bcs-bot"
$IMAGE_NAME       = "bcs-bot"
$IMAGE_TAG        = "latest"
$ENV_FILE         = ".env"

if (-not (Test-Path $ENV_FILE)) {
    Write-Host "ERROR: No se encontro el archivo $ENV_FILE con los secretos." -ForegroundColor Red
    Write-Host "Crea el archivo basandote en .env.example" -ForegroundColor Red
    exit 1
}

# --- [1/10] Resource Group ---
Write-Host "`n[1/10] Resource Group: $RESOURCE_GROUP ..." -ForegroundColor Yellow
$rgExists = az group exists --name $RESOURCE_GROUP
if ($rgExists -eq "true") {
    Write-Host "  Ya existe, omitiendo." -ForegroundColor Green
} else {
    az group create --name $RESOURCE_GROUP --location $LOCATION | Out-Null
    Write-Host "  Creado." -ForegroundColor Green
}

# --- [2/10] Container Registry ---
Write-Host "`n[2/10] Azure Container Registry: $ACR_NAME ..." -ForegroundColor Yellow
$acrExists = az acr show --name $ACR_NAME --resource-group $RESOURCE_GROUP --query "name" -o tsv 2>$null
if ($acrExists) {
    Write-Host "  Ya existe, omitiendo." -ForegroundColor Green
} else {
    az acr create --resource-group $RESOURCE_GROUP --name $ACR_NAME --sku Basic | Out-Null
    Write-Host "  Creado." -ForegroundColor Green
}

# --- [3/10] Key Vault ---
Write-Host "`n[3/10] Azure Key Vault: $KV_NAME ..." -ForegroundColor Yellow
$kvExists = az keyvault show --name $KV_NAME --resource-group $RESOURCE_GROUP --query "name" -o tsv 2>$null
if ($kvExists) {
    Write-Host "  Ya existe, omitiendo creacion." -ForegroundColor Green
} else {
    az keyvault create `
        --resource-group $RESOURCE_GROUP `
        --name $KV_NAME `
        --location $LOCATION `
        --enable-rbac-authorization false | Out-Null
    Write-Host "  Creado." -ForegroundColor Green
}

# Verificar si ya existen secretos en Key Vault
$firstSecret = az keyvault secret list --vault-name $KV_NAME --query "[0].name" -o tsv 2>$null
if ($firstSecret) {
    Write-Host "  Secretos ya existen en Key Vault, omitiendo sync." -ForegroundColor Green
} else {
    Write-Host "  Sincronizando secretos desde $ENV_FILE en Key Vault ..." -ForegroundColor Gray
    Get-Content $ENV_FILE | ForEach-Object {
        if ($_ -match "^([^#=]+)=(.+)$") {
            $kvSecretName = $matches[1].Trim() -replace "_", "-"
            $kvSecretValue = $matches[2].Trim()
            az keyvault secret set --vault-name $KV_NAME --name $kvSecretName --value $kvSecretValue | Out-Null
            Write-Host "    Synced: $kvSecretName" -ForegroundColor Gray
        }
    }
    Write-Host "  Secretos sincronizados en Key Vault" -ForegroundColor Green
}

# --- [4/10] Docker image ---
Write-Host "`n[4/10] Construyendo y subiendo imagen Docker al ACR ..." -ForegroundColor Yellow
az acr login --name $ACR_NAME

$FULL_IMAGE = "$ACR_NAME.azurecr.io/${IMAGE_NAME}:${IMAGE_TAG}"
az acr build --registry $ACR_NAME --image "${IMAGE_NAME}:${IMAGE_TAG}" .

Write-Host "  Imagen subida: $FULL_IMAGE" -ForegroundColor Green

# --- [5/10] AKS Cluster ---
Write-Host "`n[5/10] AKS Cluster: $AKS_NAME ..." -ForegroundColor Yellow
$aksExists = az aks show --resource-group $RESOURCE_GROUP --name $AKS_NAME --query "name" -o tsv 2>$null
if ($aksExists) {
    Write-Host "  Ya existe, omitiendo creacion." -ForegroundColor Green
} else {
    Write-Host "  Creando cluster (~5 min) ..." -ForegroundColor Gray
    az aks create `
        --resource-group $RESOURCE_GROUP `
        --name $AKS_NAME `
        --node-count 1 `
        --node-vm-size Standard_D2als_v7 `
        --attach-acr $ACR_NAME `
        --enable-addons azure-keyvault-secrets-provider `
        --generate-ssh-keys
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ERROR: No se pudo crear el cluster AKS." -ForegroundColor Red
        exit 1
    }
    Write-Host "  Creado." -ForegroundColor Green
}

Write-Host "`n[6/10] Obteniendo credenciales de kubectl ..." -ForegroundColor Yellow
az aks get-credentials --resource-group $RESOURCE_GROUP --name $AKS_NAME --overwrite-existing

Write-Host "`n[7/10] Configurando acceso de AKS a Key Vault ..." -ForegroundColor Yellow
$KV_IDENTITY_CLIENT_ID = az aks show `
    --resource-group $RESOURCE_GROUP `
    --name $AKS_NAME `
    --query "addonProfiles.azureKeyvaultSecretsProvider.identity.clientId" -o tsv

$TENANT_ID = az account show --query tenantId -o tsv

Write-Host "  CSI Driver Identity: $KV_IDENTITY_CLIENT_ID" -ForegroundColor Gray
Write-Host "  Tenant ID: $TENANT_ID" -ForegroundColor Gray

az keyvault set-policy `
    --name $KV_NAME `
    --spn $KV_IDENTITY_CLIENT_ID `
    --secret-permissions get list

Write-Host "  Acceso concedido al Key Vault" -ForegroundColor Green

# --- [8/10] NGINX Ingress ---
Write-Host "`n[8/10] NGINX Ingress Controller ..." -ForegroundColor Yellow
if (-not (Get-Command helm -ErrorAction SilentlyContinue)) {
    Write-Host "  Instalando Helm ..." -ForegroundColor Gray
    winget install Helm.Helm --accept-source-agreements --accept-package-agreements | Out-Null
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
}
$ingressExists = helm list -n ingress-nginx -q 2>$null | Where-Object { $_ -eq "ingress-nginx" }
if ($ingressExists) {
    Write-Host "  Ya existe, omitiendo." -ForegroundColor Green
} else {
    helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
    helm repo update

    helm install ingress-nginx ingress-nginx/ingress-nginx `
        --create-namespace `
        --namespace ingress-nginx `
        --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-dns-label-name"=$DNS_LABEL `
        --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-load-balancer-health-probe-request-path"=/healthz
}

Write-Host "  Esperando IP publica del Ingress (puede tomar ~2 min) ..." -ForegroundColor Gray
$MAX_RETRIES = 30
$RETRY = 0
$EXTERNAL_IP = ""
while ($RETRY -lt $MAX_RETRIES) {
    $EXTERNAL_IP = kubectl get svc ingress-nginx-controller -n ingress-nginx -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>$null
    if ($EXTERNAL_IP -and $EXTERNAL_IP -ne "") {
        break
    }
    Start-Sleep -Seconds 10
    $RETRY++
    Write-Host "  Reintentando ($RETRY/$MAX_RETRIES)..." -ForegroundColor Gray
}

if (-not $EXTERNAL_IP) {
    Write-Host "  ADVERTENCIA: No se obtuvo IP publica. Verifica manualmente con:" -ForegroundColor Red
    Write-Host "  kubectl get svc ingress-nginx-controller -n ingress-nginx" -ForegroundColor Red
} else {
    Write-Host "  IP Publica: $EXTERNAL_IP" -ForegroundColor Green
}

# --- [8.5] cert-manager (TLS / HTTPS) ---
Write-Host "`n[8.5] cert-manager ..." -ForegroundColor Yellow
$certManagerExists = helm list -n cert-manager -q 2>$null | Where-Object { $_ -eq "cert-manager" }
if ($certManagerExists) {
    Write-Host "  Ya existe, omitiendo." -ForegroundColor Green
} else {
    helm repo add jetstack https://charts.jetstack.io
    helm repo update
    helm install cert-manager jetstack/cert-manager `
        --namespace cert-manager `
        --create-namespace `
        --set crds.enabled=true
    Write-Host "  Esperando a que cert-manager este listo ..." -ForegroundColor Gray
    kubectl wait --for=condition=available deployment/cert-manager -n cert-manager --timeout=120s
    kubectl wait --for=condition=available deployment/cert-manager-webhook -n cert-manager --timeout=120s
    Start-Sleep -Seconds 10
    Write-Host "  cert-manager listo." -ForegroundColor Green
}

Write-Host "  Aplicando ClusterIssuer (Let's Encrypt) ..." -ForegroundColor Gray
$issuerContent = Get-Content k8s/cluster-issuer.yaml -Raw
$issuerContent = $issuerContent -replace "__ACME_EMAIL__", $ACME_EMAIL
$issuerContent | kubectl apply -f -
Write-Host "  ClusterIssuer aplicado." -ForegroundColor Green

Write-Host "`n[9/10] Aplicando manifiestos Kubernetes ..." -ForegroundColor Yellow
kubectl apply -f k8s/namespace.yaml

Write-Host "  Procesando SecretProviderClass con datos de Key Vault ..." -ForegroundColor Gray
$spcContent = Get-Content k8s/secret-provider-class.yaml -Raw
$spcContent = $spcContent -replace "__KEYVAULT_NAME__", $KV_NAME
$spcContent = $spcContent -replace "__TENANT_ID__", $TENANT_ID
$spcContent = $spcContent -replace "__CLIENT_ID__", $KV_IDENTITY_CLIENT_ID
$spcContent | kubectl apply -f -

kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml

# Forzar reinicio para que el CSI driver recargue secretos frescos de Key Vault
Write-Host "  Forzando reinicio del pod para recargar secretos ..." -ForegroundColor Gray
kubectl delete secret bcs-bot-secrets -n bcs-bot --ignore-not-found
kubectl rollout restart deployment/bcs-bot -n bcs-bot

Write-Host "`n[10/10] Verificando despliegue ..." -ForegroundColor Yellow
Write-Host "  Esperando a que los pods esten listos ..." -ForegroundColor Gray
kubectl rollout status deployment/bcs-bot -n bcs-bot --timeout=120s

Write-Host "`n=============================================" -ForegroundColor Green
Write-Host " Despliegue completado!" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green

$DOMAIN = "$DNS_LABEL.$LOCATION.cloudapp.azure.com"
Write-Host "`n  URL: https://$DOMAIN" -ForegroundColor Cyan
Write-Host "  (El certificado TLS puede tardar ~2 min en activarse)" -ForegroundColor Gray
Write-Host ""
Write-Host "  Endpoints disponibles:" -ForegroundColor White
Write-Host "    GET  https://$DOMAIN/          -> Interfaz web" -ForegroundColor White
Write-Host "    POST https://$DOMAIN/chat      -> Enviar mensaje" -ForegroundColor White
Write-Host "    POST https://$DOMAIN/reset     -> Reiniciar conversacion" -ForegroundColor White
Write-Host "    POST https://$DOMAIN/voz       -> Text-to-Speech" -ForegroundColor White
Write-Host "    POST https://$DOMAIN/transcribe -> Speech-to-Text" -ForegroundColor White
Write-Host "    GET  https://$DOMAIN/health    -> Health check" -ForegroundColor White
Write-Host ""
Write-Host "  Secretos gestionados en: Azure Key Vault ($KV_NAME)" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Para ver logs:" -ForegroundColor Gray
Write-Host "    kubectl logs -f deployment/bcs-bot -n bcs-bot" -ForegroundColor Gray
Write-Host ""
Write-Host "  Para escalar:" -ForegroundColor Gray
Write-Host "    kubectl scale deployment/bcs-bot -n bcs-bot --replicas=3" -ForegroundColor Gray
Write-Host ""
