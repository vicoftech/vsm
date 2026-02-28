# Script para obtener información de Cognito User Pool y Client
# Ejecutar desde el directorio infra/

Write-Host "=== Obteniendo información de Cognito ===" -ForegroundColor Cyan

# Intentar obtener desde Terraform outputs
Write-Host "`n1. Desde Terraform outputs:" -ForegroundColor Yellow
try {
    $poolId = terraform output -raw cognito_user_pool_id 2>$null
    $clientId = terraform output -raw cognito_user_pool_client_id 2>$null
    
    if ($poolId -and $clientId) {
        Write-Host "   User Pool ID: $poolId" -ForegroundColor Green
        Write-Host "   Client ID: $clientId" -ForegroundColor Green
    } else {
        Write-Host "   Terraform outputs no disponibles. Ejecuta 'terraform apply' primero." -ForegroundColor Red
    }
} catch {
    Write-Host "   Terraform no está inicializado o no hay outputs disponibles." -ForegroundColor Red
}

# Alternativa: Buscar en AWS directamente
Write-Host "`n2. Buscando en AWS directamente:" -ForegroundColor Yellow
try {
    # Buscar User Pool por nombre
    $poolName = "vsm-agent-users-dev"  # Ajusta según tu environment
    $pools = aws cognito-idp list-user-pools --max-results 10 --query "UserPools[?Name=='$poolName']" --output json 2>$null | ConvertFrom-Json
    
    if ($pools -and $pools.Count -gt 0) {
        $poolId = $pools[0].Id
        Write-Host "   User Pool ID encontrado: $poolId" -ForegroundColor Green
        
        # Buscar Client
        $clients = aws cognito-idp list-user-pool-clients --user-pool-id $poolId --query "UserPoolClients[?ClientName=='vsm-agent-client-dev']" --output json 2>$null | ConvertFrom-Json
        
        if ($clients -and $clients.Count -gt 0) {
            $clientId = $clients[0].ClientId
            Write-Host "   Client ID encontrado: $clientId" -ForegroundColor Green
        } else {
            Write-Host "   Client no encontrado." -ForegroundColor Yellow
        }
    } else {
        Write-Host "   User Pool no encontrado con nombre '$poolName'" -ForegroundColor Yellow
        Write-Host "   Listando todos los User Pools disponibles:" -ForegroundColor Cyan
        aws cognito-idp list-user-pools --max-results 10 --query "UserPools[*].[Name,Id]" --output table 2>$null
    }
} catch {
    Write-Host "   Error al buscar en AWS. Verifica que AWS CLI esté configurado." -ForegroundColor Red
}

Write-Host "`n=== Para crear nuevos recursos, ejecuta: ===" -ForegroundColor Cyan
Write-Host "   cd vsm-agent/infra" -ForegroundColor White
Write-Host "   terraform init" -ForegroundColor White
Write-Host "   terraform apply" -ForegroundColor White
Write-Host "   terraform output cognito_user_pool_id" -ForegroundColor White
Write-Host "   terraform output cognito_user_pool_client_id" -ForegroundColor White

