# 📋 Contrat API User System

## Base URLs
- **Prefix**: `/user-systems`
- **Tags**: `["user-systems"]`

---

## 📄 GESTION DES TYPES DE DOCUMENT (`/user-systems/document-types`)

### 1. Créer un type de document
- **Méthode**: `POST /user-systems/document-types`
- **Description**: Crée un nouveau type de document
- **Paramètres d'entrée** (Body):
  - `doc_type`: `DocumentTypeCreateRequest`
    - `name`: String (requis) - Nom du type de document
    - `description`: String (requis) - Description
    - `created_by`: String (requis) - Identifiant de l'utilisateur créateur
- **Paramètres de sortie**: `DocumentTypeResponse`
  - `slug`: String - Identifiant unique du type
  - `name`: String - Nom du type
  - `description`: String - Description
  - `status`: String - Statut (active/inactive/configuring)
  - `created_by`: String - Créateur
  - `created_at`: String (ISO 8601) - Date de création
  - `updated_at`: String (ISO 8601) - Date de mise à jour
  - `config_paths`: Dict[str, str] - Chemins des configurations

### 2. Récupérer tous les types de documents
- **Méthode**: `GET /user-systems/document-types`
- **Description**: Récupère tous les types de documents
- **Paramètres d'entrée**: Aucun
- **Paramètres de sortie**: `DocumentTypeListResponse`
  - `items`: List[`DocumentTypeResponse`] - Liste des types
  - `total`: Integer - Nombre total
  - `skip`: Integer - Décalage
  - `limit`: Integer - Limite

### 3. Récupérer un type de document par slug
- **Méthode**: `GET /user-systems/document-types/{slug}`
- **Description**: Récupère un type de document par son slug
- **Paramètres d'entrée** (Path):
  - `slug`: String (requis) - Identifiant du type
- **Paramètres de sortie**: `DocumentTypeResponse`

### 4. Mettre à jour un type de document
- **Méthode**: `PUT /user-systems/document-types/{slug}`
- **Description**: Met à jour un type de document
- **Paramètres d'entrée**:
  - **Path**: `slug`: String (requis) - Identifiant du type
  - **Body**: `update_data`: Dict[str, Any] (requis) - Données de mise à jour
- **Paramètres de sortie**: `DocumentTypeResponse`

### 5. Suppression douce d'un type de document
- **Méthode**: `DELETE /user-systems/document-types/{slug}/soft`
- **Description**: Marque un type de document pour suppression (soft delete)
- **Paramètres d'entrée** (Path):
  - `slug`: String (requis) - Identifiant du type
- **Paramètres de sortie**: `DocumentTypeDeleteResponse`
  - `status`: String - Statut de l'opération
  - `message`: String - Message descriptif
  - `deleted_slug`: String (optionnel) - Slug supprimé

### 6. Restaurer un type de document
- **Méthode**: `POST /user-systems/document-types/{slug}/restore`
- **Description**: Restaure un type de document précédemment marqué pour suppression
- **Paramètres d'entrée** (Path):
  - `slug`: String (requis) - Identifiant du type
- **Paramètres de sortie**: `DocumentTypeDeleteResponse`

### 7. Suppression définitive d'un type de document
- **Méthode**: `DELETE /user-systems/document-types/{slug}/hard`
- **Description**: Supprime définitivement un type de document
- **Paramètres d'entrée** (Path):
  - `slug`: String (requis) - Identifiant du type
- **Paramètres de sortie**: `DocumentTypeDeleteResponse`

---

## 📤 GESTION DES DOCUMENTS INITIAUX (`/user-systems/document-types/{document_type_slug}/init-documents`)

### 8. Uploader un document initial
- **Méthode**: `POST /user-systems/document-types/{document_type_slug}/init-documents`
- **Description**: Upload un document initial pour configuration
- **Paramètres d'entrée**:
  - **Path**: `document_type_slug`: String (requis) - Slug du type de document
  - **Form**: `file`: `UploadFile` (requis) - Fichier à uploader
- **Paramètres de sortie**: Dict[str, Any]
  - `filename`: String - Nom du fichier
  - `minio_path`: String - Chemin dans MinIO
  - `document_type_slug`: String - Slug du type
  - `size`: Integer - Taille en octets
  - `upload_date`: String (ISO 8601) - Date d'upload

### 9. Récupérer les documents initiaux
- **Méthode**: `GET /user-systems/document-types/{document_type_slug}/init-documents`
- **Description**: Récupère les documents initiaux
- **Paramètres d'entrée** (Path):
  - `document_type_slug`: String (requis) - Slug du type de document
- **Paramètres de sortie**: List[Dict[str, Any]]
  - `name`: String - Nom du fichier
  - `minio_path`: String - Chemin dans MinIO
  - `content_type`: String - Type MIME

---

## ⚙️ CONFIGURATION INITIALE (`/user-systems/document-types/{document_type_slug}/...`)

### 10. Construire la configuration initiale
- **Méthode**: `POST /user-systems/document-types/{document_type_slug}/build-config`
- **Description**: Construit la configuration initiale à partir des documents initiaux
- **Paramètres d'entrée** (Path):
  - `document_type_slug`: String (requis) - Slug du type de document
- **Paramètres de sortie**: Dict[str, Any]
  - `status`: String - "ok"
  - `document_type_slug`: String - Slug du type
  - `files_processed`: Integer - Nombre de fichiers traités
  - `results`: List[Dict] - Résultats par fichier

### 11. Récupérer les documents normalisés initiaux
- **Méthode**: `GET /user-systems/document-types/{document_type_slug}/normalized-init`
- **Description**: Récupère les documents normalisés initiaux
- **Paramètres d'entrée** (Path):
  - `document_type_slug`: String (requis) - Slug du type de document
- **Paramètres de sortie**: List[Dict[str, Any]]
  - `file_path`: String - Chemin du fichier
  - `file_name`: String - Nom du fichier
  - `line_count`: Integer - Nombre de lignes
  - `normalized_lines`: List - 5 premières lignes normalisées

### 12. Uploader une configuration
- **Méthode**: `POST /user-systems/document-types/{document_type_slug}/configs`
- **Description**: Upload une configuration pour un type de document
- **Paramètres d'entrée**:
  - **Path**: `document_type_slug`: String (requis) - Slug du type
  - **Body**: `config_upload`: `ConfigUpload`
    - `config_type`: String (requis) - Type de configuration (pdf_scanned, pdf_native, image, docx)
    - `config_data`: Dict[str, Any] (requis) - Données de configuration
- **Paramètres de sortie**: Dict[str, Any]
  - `status`: String - "success"
  - `document_type_slug`: String - Slug du type
  - `config_type`: String - Type de configuration
  - `config_path`: String - Chemin de la configuration

### 13. Récupérer une configuration
- **Méthode**: `GET /user-systems/document-types/{document_type_slug}/configs/{config_type}`
- **Description**: Récupère une configuration par type
- **Paramètres d'entrée** (Path):
  - `document_type_slug`: String (requis) - Slug du type
  - `config_type`: String (requis) - Type de configuration
- **Paramètres de sortie**: Dict[str, Any] - Données de configuration

### 14. Supprimer une configuration
- **Méthode**: `DELETE /user-systems/document-types/{document_type_slug}/configs/{config_type}`
- **Description**: Supprime une configuration
- **Paramètres d'entrée** (Path):
  - `document_type_slug`: String (requis) - Slug du type
  - `config_type`: String (requis) - Type de configuration
- **Paramètres de sortie**: Boolean - True si suppression réussie

---

## 🧪 ROUTES DE TEST (`/user-systems/test/{document_type_slug}/...`)

### 15. Test d'upload de documents
- **Méthode**: `POST /user-systems/test/{document_type_slug}/upload`
- **Description**: Test d'upload de documents
- **Paramètres d'entrée**:
  - **Path**: `document_type_slug`: String (requis) - Slug du type
  - **Form**: `files`: List[`UploadFile`] (requis) - Liste de fichiers
- **Paramètres de sortie**: `BatchProcessResponse`
  - `total_files`: Integer - Nombre total de fichiers
  - `processed_files`: Integer - Fichiers traités
  - `successful_files`: Integer - Fichiers traités avec succès
  - `failed_files`: Integer - Fichiers en échec
  - `results`: List[`ProcessResult`] - Résultats par fichier
  - `batch_id`: String - ID du batch
  - `source_type_stats`: Dict[str, Integer] - Statistiques par type de source

### 16. Test de récupération de documents
- **Méthode**: `GET /user-systems/test/{document_type_slug}/documents`
- **Description**: Test de récupération de documents avec pagination
- **Paramètres d'entrée**:
  - **Path**: `document_type_slug`: String (requis) - Slug du type
  - **Query**: `skip`: Integer (optionnel, défaut=0) - Décalage
  - **Query**: `limit`: Integer (optionnel, défaut=20, min=1, max=100) - Limite
- **Paramètres de sortie**: `PaginatedDocumentsResponse`
  - `items`: List[`DocumentResponse`] - Documents
  - `total`: Integer - Total de documents
  - `skip`: Integer - Décalage utilisé
  - `limit`: Integer - Limite utilisée
  - `fields`: List[Dict] - Champs extraits disponibles

### 17. Test de recherche vectorielle
- **Méthode**: `POST /user-systems/test/{document_type_slug}/search`
- **Description**: Test de recherche vectorielle avec option LLM
- **Paramètres d'entrée**:
  - **Path**: `document_type_slug`: String (requis) - Slug du type
  - **Body**: `search_request`: `VectorSearchRequest`
    - `query`: String (requis) - Requête de recherche
    - `document_type_slug`: String (requis) - Slug du type
    - `top_k`: Integer (optionnel, défaut=10) - Nombre de résultats
    - `use_llm`: Boolean (optionnel, défaut=False) - Utiliser l'IA
    - `include_content`: Boolean (optionnel, défaut=True) - Inclure le contenu
- **Paramètres de sortie**: `VectorSearchResponse` 
    - `answer`: String - Réponse générée par l'IA
    - `sources`: List[String] - Sources utilisées
    - `vector_results`: List - Résultats vectoriels bruts
    - `mode`: String - Mode utilisé ("llm_rag", "search_only", "fallback_search")

---

## 📊 SCHÉMAS DE DONNÉES

### DocumentTypeCreateRequest
- `name`: String (requis)
- `description`: String (requis)
- `created_by`: String (requis)

### DocumentTypeResponse
- `slug`: String
- `name`: String
- `description`: String
- `status`: String
- `created_by`: String
- `created_at`: String (ISO 8601)
- `updated_at`: String (ISO 8601)
- `config_paths`: Dict[str, str]

### DocumentTypeListResponse
- `items`: List[`DocumentTypeResponse`]
- `total`: Integer
- `skip`: Integer
- `limit`: Integer

### DocumentTypeDeleteResponse
- `status`: String
- `message`: String
- `deleted_slug`: String (optionnel)

### ConfigUpload
- `config_type`: String (requis)
- `config_data`: Dict[str, Any] (requis)

### VectorSearchRequest
- `query`: String (requis)
- `document_type_slug`: String (requis)
- `top_k`: Integer (optionnel, défaut=10)
- `use_llm`: Boolean (optionnel, défaut=False)
- `include_content`: Boolean (optionnel, défaut=True)

### BatchProcessResponse
- `total_files`: Integer
- `processed_files`: Integer
- `successful_files`: Integer
- `failed_files`: Integer
- `results`: List[`ProcessResult`]
- `batch_id`: String
- `source_type_stats`: Dict[str, Integer]

### ProcessResult
- `filename`: String
- `status`: String ("success" ou "error")
- `document_slug`: String (optionnel)
- `minio_path`: String (optionnel)
- `error`: String (optionnel)

### PaginatedDocumentsResponse
- `items`: List[`DocumentResponse`]
- `total`: Integer
- `skip`: Integer
- `limit`: Integer
- `fields`: List[Dict[str, str]]

### DocumentResponse
- `slug`: String
- `document_type_slug`: String
- `document_name`: String
- `minio_path`: String
- `extracted_data`: Dict[str, Any]
- `processing_date`: String (ISO 8601)
- `source_type`: String
- `metadata`: Dict[str, Any]
- `created_at`: String (ISO 8601)
- `updated_at`: String (ISO 8601)

### VectorSearchResult
- `document`: `DocumentResponse`
- `score`: Float
- `vector_content`: String (optionnel)

### VectorSearchResponse
- `answer`: String - Réponse générée par l'IA
- `sources`: List[String] - Sources utilisées
- `vector_results`: List - Résultats vectoriels bruts
- `mode`: String - Mode utilisé ("llm_rag", "search_only", "fallback_search")
---

## 🎯 CODES DE STATUT

- `200 OK`: Requête réussie
- `201 Created`: Ressource créée
- `400 Bad Request`: Requête mal formée
- `404 Not Found`: Ressource non trouvée
- `422 Validation Error`: Erreur de validation
- `500 Internal Server Error`: Erreur serveur

---

## 📝 NOTES IMPORTANTES

1. Tous les chemins sont préfixés par `/user-systems`
2. Les dates sont retournées au format ISO 8601
3. Les slugs sont utilisés comme identifiants uniques
4. La suppression douce conserve les données pendant 30 jours
5. La suppression définitive est irréversible
6. Les routes de test sont destinées aux développeurs