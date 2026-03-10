$RESOURCE_GROUP   = "rg-bcs-bot"
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

Write-Host "`n[1/10] Creando Resource Group: $RESOURCE_GROUP ..." -ForegroundColor Yellow
az group create --name $RESOURCE_GROUP --location $LOCATION

Write-Host "`n[2/10] Creando Azure Container Registry: $ACR_NAME ..." -ForegroundColor Yellow
az acr create --resource-group $RESOURCE_GROUP --name $ACR_NAME --sku Basic

Write-Host "`n[3/10] Creando Azure Key Vault: $KV_NAME ..." -ForegroundColor Yellow
az keyvault create `
    --resource-group $RESOURCE_GROUP `
    --name $KV_NAME `
    --location $LOCATION `
    --enable-rbac-authorization false

Write-Host "  Almacenando secretos desde $ENV_FILE en Key Vault ..." -ForegroundColor Gray
Get-Content $ENV_FILE | ForEach-Object {
    if ($_ -match "^([^#=]+)=(.+)$") {
        $kvSecretName = $matches[1].Trim() -replace "_", "-"
        $kvSecretValue = $matches[2].Trim()
        az keyvault secret set --vault-name $KV_NAME --name $kvSecretName --value $kvSecretValue | Out-Null
        Write-Host "    Stored: $kvSecretName" -ForegroundColor Gray
    }
}
Write-Host "  Secretos almacenados en Key Vault" -ForegroundColor Green

Write-Host "`n[4/10] Construyendo y subiendo imagen Docker al ACR ..." -ForegroundColor Yellow
az acr login --name $ACR_NAME

$FULL_IMAGE = "$ACR_NAME.azurecr.io/${IMAGE_NAME}:${IMAGE_TAG}"
docker build -t $FULL_IMAGE .
docker push $FULL_IMAGE

Write-Host "  Imagen subida: $FULL_IMAGE" -ForegroundColor Green

Write-Host "`n[5/10] Creando AKS Cluster con Key Vault CSI Driver: $AKS_NAME (~5 min) ..." -ForegroundColor Yellow
az aks create `
    --resource-group $RESOURCE_GROUP `
    --name $AKS_NAME `
    --node-count 1 `
    --node-vm-size Standard_B2s `
    --attach-acr $ACR_NAME `
    --enable-addons azure-keyvault-secrets-provider `
    --generate-ssh-keys `
    --no-wait

Write-Host "  Esperando a que el cluster este listo ..." -ForegroundColor Gray
az aks wait --resource-group $RESOURCE_GROUP --name $AKS_NAME --created

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

Write-Host "`n[8/10] Instalando NGINX Ingress Controller con DNS label '$DNS_LABEL' ..." -ForegroundColor Yellow
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update

helm install ingress-nginx ingress-nginx/ingress-nginx `
    --create-namespace `
    --namespace ingress-nginx `
    --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-dns-label-name"=$DNS_LABEL `
    --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-load-balancer-health-probe-request-path"=/healthz

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

Write-Host "`n[10/10] Verificando despliegue ..." -ForegroundColor Yellow
Write-Host "  Esperando a que los pods esten listos ..." -ForegroundColor Gray
kubectl wait --for=condition=available deployment/bcs-bot -n bcs-bot --timeout=120s

Write-Host "`n=============================================" -ForegroundColor Green
Write-Host " Despliegue completado!" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green

$DOMAIN = "$DNS_LABEL.$LOCATION.cloudapp.azure.com"
Write-Host "`n  URL: http://$DOMAIN" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Endpoints disponibles:" -ForegroundColor White
Write-Host "    GET  http://$DOMAIN/          -> Interfaz web" -ForegroundColor White
Write-Host "    POST http://$DOMAIN/chat      -> Enviar mensaje" -ForegroundColor White
Write-Host "    POST http://$DOMAIN/reset     -> Reiniciar conversacion" -ForegroundColor White
Write-Host "    POST http://$DOMAIN/voz       -> Text-to-Speech" -ForegroundColor White
Write-Host "    POST http://$DOMAIN/transcribe -> Speech-to-Text" -ForegroundColor White
Write-Host "    GET  http://$DOMAIN/health    -> Health check" -ForegroundColor White
Write-Host ""
Write-Host "  Secretos gestionados en: Azure Key Vault ($KV_NAME)" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Para ver logs:" -ForegroundColor Gray
Write-Host "    kubectl logs -f deployment/bcs-bot -n bcs-bot" -ForegroundColor Gray
Write-Host ""
Write-Host "  Para escalar:" -ForegroundColor Gray
Write-Host "    kubectl scale deployment/bcs-bot -n bcs-bot --replicas=3" -ForegroundColor Gray
Write-Host ""
