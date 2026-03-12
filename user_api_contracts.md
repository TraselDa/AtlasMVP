# 📋 Contrat API User

## Base URLs
- **Prefix**: `/users`
- **Tags**: `["users"]`

---

## 📄 GESTION DES TYPES DE DOCUMENT UTILISATEUR (`/users/document-types`)

### 1. Récupérer tous les types de documents
- **Méthode**: `GET /users/document-types`
- **Description**: Récupère tous les types de documents actifs avec pagination
- **Paramètres d'entrée** (Query):
  - `skip`: Integer (optionnel, défaut=0, min=0) - Nombre d'éléments à sauter
  - `limit`: Integer (optionnel, défaut=100, min=1, max=1000) - Nombre maximum d'éléments à retourner
- **Paramètres de sortie**: `DocumentTypeListResponse`
  - `items`: List[`DocumentTypeResponse`] - Liste des types de documents
  - `total`: Integer - Nombre total de types
  - `skip`: Integer - Décalage utilisé
  - `limit`: Integer - Limite utilisée

### 2. Récupérer un type de document par slug
- **Méthode**: `GET /users/document-types/{slug}`
- **Description**: Récupère un type de document par son slug
- **Paramètres d'entrée** (Path):
  - `slug`: String (requis) - Identifiant unique du type de document
- **Paramètres de sortie**: `DocumentTypeResponse`
  - `slug`: String - Identifiant du type
  - `name`: String - Nom du type
  - `description`: String - Description
  - `status`: String - Statut
  - `created_by`: String - Créateur
  - `created_at`: String (ISO 8601) - Date de création
  - `updated_at`: String (ISO 8601) - Date de mise à jour
  - `config_paths`: Dict[str, str] - Chemins des configurations

### 3. Récupérer les statistiques d'un type de document
- **Méthode**: `GET /users/document-types/{slug}/stats`
- **Description**: Récupère les statistiques d'un type de document
- **Paramètres d'entrée** (Path):
  - `slug`: String (requis) - Identifiant du type de document
- **Paramètres de sortie**: `DocumentTypeStatsResponse`
  - `total_documents`: Integer - Nombre total de documents
  - `active_documents`: Integer - Documents actifs
  - `by_source_type`: Dict[str, Integer] - Répartition par type de source
  - `config_status`: Dict[str, Boolean] - État des configurations
  - `last_updated`: String (ISO 8601) - Dernière mise à jour

---

## 📤 GESTION DES DOCUMENTS UTILISATEUR (`/users/documents`)

### 4. Uploader et traiter plusieurs documents
- **Méthode**: `POST /users/documents/upload`
- **Description**: Upload et traite plusieurs documents simultanément
- **Paramètres d'entrée**:
  - **Query**: `document_type_slug`: String (requis) - Slug du type de document
  - **Form**: `files`: List[`UploadFile`] (requis) - Liste de fichiers (max 50)
- **Validation**:
  - Maximum 50 fichiers par requête
  - Au moins 1 fichier requis
- **Paramètres de sortie**: `BatchProcessResponse`
  - `total_files`: Integer - Nombre total de fichiers
  - `processed_files`: Integer - Fichiers traités
  - `successful_files`: Integer - Fichiers traités avec succès
  - `failed_files`: Integer - Fichiers en échec
  - `results`: List[`ProcessResult`] - Résultats par fichier
  - `batch_id`: String - ID du batch
  - `source_type_stats`: Dict[str, Integer] - Statistiques par type de source

### 5. Récupérer les documents d'un type spécifique
- **Méthode**: `GET /users/documents/{document_type_slug}`
- **Description**: Récupère les documents d'un type spécifique avec pagination
- **Paramètres d'entrée**:
  - **Path**: `document_type_slug`: String (requis) - Slug du type de document
  - **Query**: `skip`: Integer (optionnel, défaut=0, min=0) - Nombre d'éléments à sauter
  - **Query**: `limit`: Integer (optionnel, défaut=20, min=1, max=100) - Nombre maximum d'éléments
- **Paramètres de sortie**: `PaginatedDocumentsResponse`
  - `items`: List[`DocumentResponse`] - Liste des documents
  - `total`: Integer - Nombre total de documents
  - `skip`: Integer - Décalage utilisé
  - `limit`: Integer - Limite utilisée
  - `fields`: List[Dict[str, str]] - Champs extraits disponibles

### 6. Filtrer les documents avec pagination
- **Méthode**: `POST /users/documents/{document_type_slug}/filter`
- **Description**: Filtre les documents avec pagination
- **Paramètres d'entrée**:
  - **Path**: `document_type_slug`: String (requis) - Slug du type de document
  - **Body**: `filter_request`: `DocumentFilterRequest`
    - `filters`: Dict[str, Any] (requis) - Critères de filtrage
    - `skip`: Integer (optionnel, défaut=0) - Décalage
    - `limit`: Integer (optionnel, défaut=20) - Limite
- **Paramètres de sortie**: `PaginatedDocumentsResponse`

### 7. Récupérer un document par son slug
- **Méthode**: `GET /users/documents/{document_type_slug}/{document_slug}`
- **Description**: Récupère un document par son slug
- **Paramètres d'entrée** (Path):
  - `document_type_slug`: String (requis) - Slug du type de document
  - `document_slug`: String (requis) - Slug du document
- **Paramètres de sortie**: `DocumentResponse`
  - `slug`: String - Identifiant du document
  - `document_type_slug`: String - Type de document
  - `document_name`: String - Nom du fichier
  - `minio_path`: String - Chemin dans MinIO
  - `extracted_data`: Dict[str, Any] - Données extraites
  - `processing_date`: String (ISO 8601) - Date de traitement
  - `source_type`: String - Type de source
  - `metadata`: Dict[str, Any] - Métadonnées
  - `created_at`: String (ISO 8601) - Date de création
  - `updated_at`: String (ISO 8601) - Date de mise à jour

### 8. Recherche vectorielle avec/sans LLM
- **Méthode**: `POST /users/documents/{document_type_slug}/search`
- **Description**: Effectue une recherche vectorielle avec option de réponse par IA
- **Paramètres d'entrée**:
  - **Path**: `document_type_slug`: String (requis) - Slug du type de document
  - **Body**: `search_request`: `VectorSearchRequest`
    - `query`: String (requis) - Requête de recherche
    - `document_type_slug`: String (requis) - Slug du type
    - `top_k`: Integer (optionnel, défaut=10) - Nombre de résultats
    - `use_llm`: Boolean (optionnel, défaut=False) - Utiliser l'IA pour générer une réponse
    - `include_content`: Boolean (optionnel, défaut=True) - Inclure le contenu vectoriel
- **Paramètres de sortie**: Variable selon `use_llm`
  - Type: `VectorSearchResponse`
  - `answer`: String - Réponse générée par l'IA
  - `sources`: List[String] - Sources utilisées
  - `vector_results`: List - Résultats vectoriels bruts
  - `mode`: String - Mode utilisé ("llm_rag", "search_only", "fallback_search")
  - `error`: String (optionnel) - Message d'erreur en cas de fallback

### 9. Supprimer un document (soft delete)
- **Méthode**: `DELETE /users/documents/{document_type_slug}/{document_slug}`
- **Description**: Supprime un document (soft delete)
- **Paramètres d'entrée** (Path):
  - `document_type_slug`: String (requis) - Slug du type de document
  - `document_slug`: String (requis) - Slug du document
- **Paramètres de sortie**: `DocumentDeleteResponse`
  - `status`: String - Statut de l'opération ("success" ou "error")
  - `message`: String - Message descriptif
  - `deleted_slug`: String (optionnel) - Slug du document supprimé

### 10. Récupérer les statistiques des documents d'un type
- **Méthode**: `GET /users/documents/{document_type_slug}/stats`
- **Description**: Récupère les statistiques des documents d'un type spécifique
- **Paramètres d'entrée** (Path):
  - `document_type_slug`: String (requis) - Slug du type de document
- **Paramètres de sortie**: `DocumentStatsResponse`
  - `total_documents`: Integer - Documents totaux
  - `processed_documents`: Integer - Documents traités
  - `vectorized_documents`: Integer - Documents vectorisés
  - `by_source_type`: Dict[str, Integer] - Répartition par type de source
  - `by_month`: Dict[str, Integer] - Évolution mensuelle (12 derniers mois)
  - `field_summary`: List[`DocumentFieldSummary`] - Résumé des champs extraits

---

## 📊 SCHÉMAS DE DONNÉES DÉTAILLÉS

### DocumentFilterRequest
- `filters`: Dict[str, Any] (requis) - Critères de filtrage
- `skip`: Integer (optionnel, défaut=0) - Décalage
- `limit`: Integer (optionnel, défaut=20) - Limite

### ProcessResult
- `filename`: String - Nom du fichier
- `status`: String - Statut ("success" ou "error")
- `document_slug`: String (optionnel) - Slug du document créé
- `minio_path`: String (optionnel) - Chemin dans MinIO
- `error`: String (optionnel) - Message d'erreur

### VectorSearchResult
- `document`: `DocumentResponse` - Document trouvé
- `score`: Float - Score de similarité
- `vector_content`: String (optionnel) - Contenu vectoriel

### DocumentFieldSummary
- `field_name`: String - Nom du champ
- `field_type`: String - Type de données
- `sample_values`: List[Any] - Valeurs d'exemple
- `count`: Integer - Nombre d'occurrences

### Types de source supportés:
- `pdf_scanned` - PDF scanné (image)
- `pdf_native` - PDF natif (texte)
- `image` - Image (PNG, JPG, JPEG)
- `docx` - Document Word
- `unknown` - Type inconnu

---

## ⚠️ LIMITATIONS ET VALIDATIONS

### Upload de documents:
- Maximum 50 fichiers par requête
- Formats supportés: PDF, PNG, JPG, JPEG, DOCX
- Taille maximale: Dépend de la configuration FastAPI (défaut 100MB)

### Pagination:
- `skip`: Minimum 0
- `limit`: Minimum 1, Maximum 1000 pour les types, 100 pour les documents

### Filtrage:
- Les filtres peuvent porter sur:
  - Les champs extraits (`extracted_data.field_name`)
  - Les métadonnées (`metadata.key`)
  - Le type de source (`source_type`)
  - La date de traitement (`processing_date`)

---

## 🎯 CODES DE STATUT

- `200 OK`: Requête réussie
- `201 Created`: Ressource créée (upload)
- `400 Bad Request`:
  - Aucun fichier fourni
  - Trop de fichiers (>50)
  - Format de fichier non supporté
- `404 Not Found`:
  - Type de document inexistant
  - Document inexistant
- `422 Validation Error`: Paramètres invalides
- `500 Internal Server Error`: Erreur serveur

---

## 📝 NOTES IMPORTANTES

1. **Authentification**: Ces routes sont destinées aux utilisateurs authentifiés
2. **Permissions**: L'utilisateur doit avoir accès au type de document
3. **Soft Delete**: La suppression de document est réversible pendant 30 jours
4. **Recherche LLM**: En cas d'indisponibilité du service LLM, retour automatique en mode recherche simple
5. **Batch Processing**: Le traitement par lots est asynchrone, les résultats sont immédiats mais le traitement continue en arrière-plan
6. **Formats de date**: Toutes les dates sont en ISO 8601 (YYYY-MM-DDTHH:MM:SS.sssZ)