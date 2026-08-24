
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
# ============================================================
# SCRIPT : Extraction des 8 premières colonnes des fichiers *plan*.csv
# DESCRIPTION : Extrait uniquement les colonnes :
#               N° semaine;Jour;Date;Discipline;Type de séance;Détails;Durée (min);Journée type
# ============================================================

# ----- 1. Definir les chemins -----
$sourceRoot = "D:\DevPython\Deepseek-athlete\outputs\plans"
$outputFile = "D:\DevPython\Deepseek-athlete\outputs\plans\fusion_plans_8_colonnes.csv"

# ----- 2. Verifier que le dossier source existe -----
if (-not (Test-Path $sourceRoot)) {
    Write-Host "ERREUR : Le dossier source '$sourceRoot' n'existe pas." -ForegroundColor Red
    exit 1
}

# ----- 3. Recuperer tous les fichiers *plan*.csv (dans tous les sous-dossiers) -----
$csvFiles = Get-ChildItem -Path $sourceRoot -Filter "*plan*.csv" -Recurse -File

# ----- 4. Verifier qu'il y a au moins un fichier -----
if ($csvFiles.Count -eq 0) {
    Write-Host "Aucun fichier '*plan*.csv' trouve dans '$sourceRoot' et ses sous-dossiers." -ForegroundColor Yellow
    exit 0
}

# ----- 5. Supprimer l'ancien fichier de fusion s'il existe -----
if (Test-Path $outputFile) {
    Remove-Item -Path $outputFile -Force
    Write-Host "Ancien fichier de fusion supprime." -ForegroundColor Gray
}

# ----- 6. Initialiser le compteur -----
$fileCount = 0
$totalLines = 0

# ----- 7. Ecrire l'en-tete du fichier de fusion (8 colonnes) -----
$header = "# ============================================================"
$header += "`n# FUSION DES PLANS (8 COLONNES) - $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
$header += "`n# Colonnes : N° semaine;Jour;Date;Discipline;Type de séance;Détails;Durée (min);Journée type"
$header += "`n# Nombre de fichiers fusionnes : $($csvFiles.Count)"
$header += "`n# ============================================================"
$header += "`n"
$header += "N° semaine;Jour;Date;Discipline;Type de séance;Détails;Durée (min);Journée type"

Add-Content -Path $outputFile -Value $header -Encoding UTF8

# ----- 8. Parcourir chaque fichier CSV -----
foreach ($file in $csvFiles) {
    $fileCount++
    
    # Separateur visible entre les fichiers
    $separator = "`n"
    $separator += "# ============================================================"
    $separator += "`n# FICHIER N°$fileCount : $($file.Name)"
    $separator += "`n# ============================================================"
    
    Add-Content -Path $outputFile -Value $separator -Encoding UTF8
    
    # Lire le fichier ligne par ligne
    try {
        $lines = Get-Content -Path $file.FullName -Encoding UTF8
        $lineNumber = 0
        $fileLineCount = 0
        
        foreach ($line in $lines) {
            $lineNumber++
            
            # Ignorer les lignes vides
            if ([string]::IsNullOrWhiteSpace($line)) {
                continue
            }
            
            # ----- Extraire les 8 premieres colonnes -----
            # On utilise -split avec une limite de 9 pour garder les 8 premieres colonnes
            # (le séparateur est le point-virgule)
            $columns = $line -split ';', 9
            
            # Si on a moins de 8 colonnes, on complete avec des colonnes vides
            while ($columns.Count -lt 8) {
                $columns += ""
            }
            
            # Prendre les 8 premieres colonnes
            $extractedLine = $columns[0..7] -join ';'
            
            # Ajouter au fichier de sortie (sauf si c'est la ligne d'en-tete originale)
            if ($lineNumber -eq 1 -and $extractedLine -like "*N° semaine*") {
                # Ignorer l'en-tete original, on a deja le notre
                continue
            }
            
            Add-Content -Path $outputFile -Value $extractedLine -Encoding UTF8
            $fileLineCount++
            $totalLines++
        }
        
        Write-Host "OK Fichier $fileCount/$($csvFiles.Count) : $($file.Name) ($fileLineCount lignes extraites)" -ForegroundColor Green
    }
    catch {
        Write-Host "ERREUR lors de la lecture de $($file.Name) : $_" -ForegroundColor Red
    }
}

# ----- 9. Ajouter un pied de page -----
$footer = "`n"
$footer += "# ============================================================"
$footer += "`n# FIN DE LA FUSION - $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
$footer += "`n# Total fichiers : $fileCount"
$footer += "`n# Total lignes extraites : $totalLines"
$footer += "`n# Fichier de sortie : $outputFile"
$footer += "`n# ============================================================"

Add-Content -Path $outputFile -Value $footer -Encoding UTF8

# ----- 10. Resume final -----
Write-Host ""
Write-Host "EXTRACTION TERMINEE !" -ForegroundColor Green
Write-Host "Fichier genere : $outputFile" -ForegroundColor Cyan
Write-Host "Nombre de fichiers traites : $fileCount" -ForegroundColor Cyan
Write-Host "Total de lignes extraites : $totalLines" -ForegroundColor Cyan
Write-Host "Taille du fichier : $([math]::Round((Get-Item $outputFile).Length / 1KB, 2)) KB" -ForegroundColor Cyan