#!/bin/bash

# =============================================================================
# Script de gestion des secrets (chiffrement/déchiffrement des fichiers .env)
# Utilise 'age' pour le chiffrement (https://github.com/FiloSottile/age)
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
KEY_FILE="$ROOT_DIR/.secrets-key"

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Liste des fichiers .env à chiffrer (chemins relatifs depuis la racine)
ENV_FILES=(
    # Backend Docker
    "backend/infra/env/.backend.dev.env"
    "backend/infra/env/.backend.prod.env"
    "backend/infra/env/.backend.qa.env"
    # LLM Core
    "llm_core/backend.dev.env"
    "llm_core/backend.prod.env"
    "llm_core/backend.qa.env"
)

# Vérifie si age est installé
check_age() {
    if ! command -v age &> /dev/null; then
        echo -e "${RED}Erreur: 'age' n'est pas installé.${NC}"
        echo -e "Installez-le avec: ${BLUE}brew install age${NC}"
        exit 1
    fi
}

# Génère une nouvelle clé si elle n'existe pas
generate_key() {
    if [ -f "$KEY_FILE" ]; then
        echo -e "${YELLOW}La clé existe déjà: $KEY_FILE${NC}"
        return
    fi

    echo -e "${BLUE}Génération d'une nouvelle clé...${NC}"
    age-keygen -o "$KEY_FILE" 2>/dev/null
    chmod 600 "$KEY_FILE"
    echo -e "${GREEN}Clé générée: $KEY_FILE${NC}"
    echo -e "${RED}IMPORTANT: Ne commitez JAMAIS ce fichier!${NC}"
    echo -e "${YELLOW}Partagez cette clé de manière sécurisée avec votre équipe.${NC}"
}

# Récupère la clé publique depuis le fichier de clé
get_public_key() {
    if [ ! -f "$KEY_FILE" ]; then
        echo -e "${RED}Erreur: Fichier de clé non trouvé: $KEY_FILE${NC}"
        echo -e "Exécutez d'abord: ${BLUE}$0 generate-key${NC}"
        exit 1
    fi
    grep "public key:" "$KEY_FILE" | sed 's/.*public key: //'
}

# Chiffre un fichier
encrypt_file() {
    local file="$1"
    local full_path="$ROOT_DIR/$file"
    local encrypted_path="${full_path}.enc"

    if [ ! -f "$full_path" ]; then
        echo -e "${YELLOW}  Ignoré (n'existe pas): $file${NC}"
        return
    fi

    local public_key=$(get_public_key)
    age -r "$public_key" -o "$encrypted_path" "$full_path"
    echo -e "${GREEN}  Chiffré: $file -> ${file}.enc${NC}"
}

# Déchiffre un fichier
decrypt_file() {
    local file="$1"
    local full_path="$ROOT_DIR/$file"
    local encrypted_path="${full_path}.enc"

    if [ ! -f "$encrypted_path" ]; then
        echo -e "${YELLOW}  Ignoré (fichier chiffré n'existe pas): ${file}.enc${NC}"
        return
    fi

    if [ ! -f "$KEY_FILE" ]; then
        echo -e "${RED}Erreur: Fichier de clé non trouvé: $KEY_FILE${NC}"
        exit 1
    fi

    age -d -i "$KEY_FILE" -o "$full_path" "$encrypted_path"
    echo -e "${GREEN}  Déchiffré: ${file}.enc -> $file${NC}"
}

# Chiffre tous les fichiers .env
encrypt_all() {
    echo -e "${BLUE}Chiffrement des fichiers .env...${NC}"
    echo ""

    for file in "${ENV_FILES[@]}"; do
        encrypt_file "$file"
    done

    echo ""
    echo -e "${GREEN}Chiffrement terminé!${NC}"
    echo -e "${YELLOW}Les fichiers .enc peuvent être commités en toute sécurité.${NC}"
}

# Déchiffre tous les fichiers .env
decrypt_all() {
    echo -e "${BLUE}Déchiffrement des fichiers .env...${NC}"
    echo ""

    for file in "${ENV_FILES[@]}"; do
        decrypt_file "$file"
    done

    echo ""
    echo -e "${GREEN}Déchiffrement terminé!${NC}"
}

# Liste les fichiers gérés
list_files() {
    echo -e "${BLUE}Fichiers .env gérés:${NC}"
    echo ""

    for file in "${ENV_FILES[@]}"; do
        local full_path="$ROOT_DIR/$file"
        local encrypted_path="${full_path}.enc"

        local status=""
        if [ -f "$full_path" ] && [ -f "$encrypted_path" ]; then
            status="${GREEN}[clair + chiffré]${NC}"
        elif [ -f "$full_path" ]; then
            status="${YELLOW}[clair uniquement]${NC}"
        elif [ -f "$encrypted_path" ]; then
            status="${BLUE}[chiffré uniquement]${NC}"
        else
            status="${RED}[absent]${NC}"
        fi

        echo -e "  $file $status"
    done
}

# Affiche la clé publique
show_public_key() {
    if [ ! -f "$KEY_FILE" ]; then
        echo -e "${RED}Erreur: Fichier de clé non trouvé: $KEY_FILE${NC}"
        echo -e "Exécutez d'abord: ${BLUE}$0 generate-key${NC}"
        exit 1
    fi

    echo -e "${BLUE}Clé publique:${NC}"
    get_public_key
}

# Supprime les fichiers en clair (après chiffrement)
clean() {
    echo -e "${YELLOW}Suppression des fichiers .env en clair...${NC}"
    echo ""

    for file in "${ENV_FILES[@]}"; do
        local full_path="$ROOT_DIR/$file"
        if [ -f "$full_path" ]; then
            rm "$full_path"
            echo -e "${RED}  Supprimé: $file${NC}"
        fi
    done

    echo ""
    echo -e "${GREEN}Nettoyage terminé!${NC}"
}

# Affiche l'aide
show_help() {
    echo "Usage: $0 <commande>"
    echo ""
    echo "Commandes:"
    echo "  generate-key    Génère une nouvelle clé de chiffrement"
    echo "  encrypt         Chiffre tous les fichiers .env"
    echo "  decrypt         Déchiffre tous les fichiers .env"
    echo "  list            Liste les fichiers gérés et leur statut"
    echo "  public-key      Affiche la clé publique"
    echo "  clean           Supprime les fichiers .env en clair"
    echo "  help            Affiche cette aide"
    echo ""
    echo "Workflow recommandé:"
    echo "  1. generate-key  # Une seule fois, partager la clé avec l'équipe"
    echo "  2. encrypt       # Après modification des .env"
    echo "  3. git commit    # Commiter les fichiers .enc"
    echo "  4. decrypt       # Sur une nouvelle machine avec la clé"
}

# Main
check_age

case "${1:-help}" in
    generate-key)
        generate_key
        ;;
    encrypt)
        encrypt_all
        ;;
    decrypt)
        decrypt_all
        ;;
    list)
        list_files
        ;;
    public-key)
        show_public_key
        ;;
    clean)
        clean
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo -e "${RED}Commande inconnue: $1${NC}"
        echo ""
        show_help
        exit 1
        ;;
esac
