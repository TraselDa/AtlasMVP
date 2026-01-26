class NotFoundException(Exception):
    def __init__(self, message: str = "Ressource non trouvée"):
        self.message = message
        super().__init__(self.message)

class ValidationException(Exception):
    def __init__(self, message: str = "Données invalides"):
        self.message = message
        super().__init__(self.message)

class AuthenticationException(Exception):
    def __init__(self, message: str = "Authentification requise"):
        self.message = message
        super().__init__(self.message)

class AuthorizationException(Exception):
    def __init__(self, message: str = "Non autorisé"):
        self.message = message
        super().__init__(self.message)

class ProcessingException(Exception):
    def __init__(self, message: str = "Erreur lors du traitement"):
        self.message = message
        super().__init__(self.message)

class StorageException(Exception):
    def __init__(self, message: str = "Erreur de stockage"):
        self.message = message
        super().__init__(self.message)


class VectorException(Exception):
    def __init__(self, message: str = "Erreur lors de l'opération vectorielle"):
        self.message = message
        super().__init__(self.message)

class ProcessingException(Exception):
    def __init__(self, message: str = "Erreur lors du traitement"):
        self.message = message
        super().__init__(self.message)

class StorageException(Exception):
    def __init__(self, message: str = "Erreur de stockage"):
        self.message = message
        super().__init__(self.message)

class OCRException(Exception):
    def __init__(self, message: str = "Erreur lors de l'OCR"):
        self.message = message
        super().__init__(self.message)        