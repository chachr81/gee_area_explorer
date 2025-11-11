"""
Utilidades para configuración de Google Earth Engine.
Manejo seguro de credenciales y project ID.
"""

import sys
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv, dotenv_values
import logging


# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/gee_toolkit.log')
    ]
)
logger = logging.getLogger(__name__)


class GEEConfig:
    """Gestor de configuración para Google Earth Engine."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.env_file = self.project_root / '.env'
        self.env_example = self.project_root / '.env.example'
        
        # Crear carpeta logs si no existe
        logs_dir = self.project_root / 'logs'
        logs_dir.mkdir(exist_ok=True)
        
        load_dotenv(self.env_file)
        self._env_values = dotenv_values(self.env_file)
    
    def get_project_id(self) -> Optional[str]:
        """
        Obtiene el Project ID desde:
        1. Variable de entorno GEE_PROJECT
        2. Archivo .env
        3. Guía interactiva si no existe
        
        Returns:
            Project ID o None si no se pudo obtener
        """
        project_id = self._env_values.get('GEE_PROJECT')
        
        if project_id and project_id != 'your-project-id-here':
            logger.info(f"Project ID encontrado: {project_id}")
            return project_id
        
        # Si no existe .env, guiar al usuario
        if not self.env_file.exists():
            return self._setup_interactive()
        
        return None
    
    def _setup_interactive(self) -> Optional[str]:
        """
        Guía interactiva para configurar el proyecto por primera vez.
        
        Returns:
            Project ID ingresado por el usuario
        """
        print("\n" + "="*80)
        print("CONFIGURACIÓN INICIAL - GOOGLE EARTH ENGINE")
        print("="*80)
        print("\nNo encontré archivo .env con tu proyecto configurado.")
        print("Vamos a configurarlo ahora (solo esta vez).\n")
        
        print("PASOS PARA OBTENER UN PROJECT ID:")
        print("-" * 80)
        print("1. Ve a: https://console.cloud.google.com/projectcreate")
        print("2. Crea un nuevo proyecto (ej: 'mi-gee-proyecto')")
        print("3. IMPORTANTE: Copia el 'Project ID', NO el nombre del proyecto")
        print("   - El Project ID tiene formato: mi-proyecto-123456")
        print("   - Aparece debajo del nombre del proyecto")
        print("\n4. Registra el proyecto en Earth Engine:")
        print("   https://code.earthengine.google.com/register")
        print("   (Selecciona 'Unpaid usage' o el plan que prefieras)")
        print("-" * 80)
        
        # Opción de omitir
        print("\nOPCIONES:")
        print("  - Ingresa tu Project ID ahora")
        print("  - Presiona ENTER para configurar después")
        print("  - Presiona 'q' para salir")
        
        try:
            user_input = input("\nProject ID: ").strip()
            
            if user_input.lower() == 'q':
                print("\n[INFO] Configuración cancelada.")
                sys.exit(0)
            
            if not user_input:
                print("\n[WARN] Configuración omitida.")
                print("[INFO] Puedes configurarlo después creando el archivo .env")
                print(f"       Usa .env.example como template: {self.env_example}")
                return None
            
            # Validar formato básico del Project ID
            if not self._validate_project_id(user_input):
                print("\n[WARN] El Project ID no parece válido.")
                print("       Formato esperado: minúsculas, números y guiones")
                print("       Ejemplo: mi-proyecto-123456")
                retry = input("\n¿Reintentar? (s/n): ").strip().lower()
                if retry == 's':
                    return self._setup_interactive()
                return None
            
            # Guardar en .env
            if self._save_to_env(user_input):
                print(f"\n[OK] Proyecto configurado: {user_input}")
                print(f"[OK] Guardado en: {self.env_file}")
                print("[OK] Listo! Nunca más te lo volveremos a preguntar.\n")
                return user_input
            else:
                print("\n[ERROR] Error al guardar configuración.")
                return None
                
        except KeyboardInterrupt:
            print("\n\n[INFO] Configuración cancelada.")
            sys.exit(0)
    
    def _validate_project_id(self, project_id: str) -> bool:
        """
        Valida formato básico del Project ID.
        
        Args:
            project_id: Project ID a validar
            
        Returns:
            True si el formato es válido
        """
        if not project_id:
            return False
        
        # Project ID debe tener entre 6 y 30 caracteres
        if len(project_id) < 6 or len(project_id) > 30:
            return False
        
        # Solo minúsculas, números y guiones
        # No puede empezar con número o guion
        if not project_id[0].isalpha():
            return False
        
        allowed_chars = set('abcdefghijklmnopqrstuvwxyz0123456789-')
        if not all(c in allowed_chars for c in project_id):
            return False
        
        return True
    
    def _save_to_env(self, project_id: str) -> bool:
        """
        Guarda el Project ID en archivo .env
        
        Args:
            project_id: Project ID a guardar
            
        Returns:
            True si se guardó exitosamente
        """
        try:
            # Crear .env desde .env.example si existe
            content = ""
            if self.env_example.exists():
                content = self.env_example.read_text()
                # Reemplazar el placeholder
                content = content.replace('your-project-id-here', project_id)
            else:
                content = f"# Google Earth Engine Configuration\nGEE_PROJECT={project_id}\n"
            
            self.env_file.write_text(content)
            
            # Recargar variables de entorno
            load_dotenv(self.env_file, override=True)
            
            return True
        except Exception as e:
            print(f"\n[ERROR] Error al guardar: {e}")
            return False
    
    def validate_credentials(self) -> bool:
        """
        Verifica que existan credenciales de Earth Engine.
        
        Returns:
            True si las credenciales existen
        """
        credentials_path = Path.home() / '.config' / 'earthengine' / 'credentials'
        return credentials_path.exists()
    
    def print_status(self):
        """Imprime resumen de configuración actual."""
        print("\n" + "="*80)
        print("ESTADO DE CONFIGURACIÓN")
        print("="*80)
        
        # Project ID
        project_id = self._env_values.get('GEE_PROJECT')
        if project_id and project_id != 'your-project-id-here':
            print(f"[OK] Project ID: {project_id}")
            logger.info(f"Project ID configurado: {project_id}")
        else:
            print("[WARN] Project ID: No configurado")
            logger.warning("Project ID no configurado")
        
        # Credenciales
        if self.validate_credentials():
            print("[OK] Credenciales: Encontradas")
        else:
            print("[WARN] Credenciales: No encontradas")
            print("       Ejecuta: earthengine authenticate")
        
        # Archivo .env
        if self.env_file.exists():
            print(f"[OK] Archivo .env: {self.env_file}")
        else:
            print(f"[WARN] Archivo .env: No existe")
            print(f"       Template: {self.env_example}")
        
        print("="*80 + "\n")


def get_project_id() -> Optional[str]:
    """
    Función helper para obtener el Project ID.
    Uso simple desde cualquier script.
    
    Returns:
        Project ID configurado o None
    """
    config = GEEConfig()
    return config.get_project_id()


def validate_setup() -> bool:
    """
    Valida que la configuración esté completa.
    
    Returns:
        True si todo está configurado correctamente
    """
    config = GEEConfig()
    project_id = config.get_project_id()
    credentials_ok = config.validate_credentials()
    
    return bool(project_id) and credentials_ok
