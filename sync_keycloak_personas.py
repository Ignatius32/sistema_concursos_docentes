#!/usr/bin/env python3
"""
Command-line interface for Keycloak-Persona synchronization.

Usage:
    python sync_keycloak_personas.py --help
    python sync_keycloak_personas.py --dry-run
    python sync_keycloak_personas.py --full-sync
    python sync_keycloak_personas.py --personas-to-keycloak
    python sync_keycloak_personas.py --keycloak-to-personas
    python sync_keycloak_personas.py --remove-orphaned --confirm
"""

import argparse
import json
import sys
import os
from datetime import datetime

# Add the app directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.services.keycloak_persona_sync import get_sync_service


def print_results(results, operation_name):
    """Print sync results in a readable format."""
    print(f"\n{'='*60}")
    print(f"RESULTADOS DE {operation_name.upper()}")
    print(f"{'='*60}")
    
    if not results.get('success', False):
        print(f"❌ ERROR: {results.get('error', 'Operación falló')}")
        return
    
    print(f"✅ Operación completada exitosamente")
    print(f"⏰ Timestamp: {results.get('timestamp', 'N/A')}")
    print(f"🧪 Modo simulación: {'Sí' if results.get('dry_run', False) else 'No'}")
    
    # Print summary if available
    if 'summary' in results:
        summary = results['summary']
        print(f"\n📊 RESUMEN:")
        print(f"   • Creados en Keycloak: {summary.get('personas_created_in_keycloak', 0)}")
        print(f"   • Creados localmente: {summary.get('personas_created_locally', 0)}")
        print(f"   • Registros sincronizados: {summary.get('records_synchronized', 0)}")
        print(f"   • Total errores: {summary.get('total_errors', 0)}")
    
    # Print detailed results
    sections = [
        ('personas_to_keycloak', 'PERSONAS → KEYCLOAK'),
        ('keycloak_to_personas', 'KEYCLOAK → PERSONAS'),
        ('updates', 'ACTUALIZACIONES'),
        ('results', 'RESULTADOS')  # For partial syncs
    ]
    
    for section_key, section_title in sections:
        if section_key in results and results[section_key]:
            section_data = results[section_key]
            print(f"\n📋 {section_title}:")
            
            # Print counts
            created = section_data.get('created', [])
            updated = section_data.get('updated', [])
            errors = section_data.get('errors', [])
            removed = section_data.get('removed', [])
            synchronized = section_data.get('synchronized', [])
            
            if created:
                print(f"   ✅ Creados: {len(created)}")
                if len(created) <= 10:  # Show details for small lists
                    for item in created:
                        if isinstance(item, dict):
                            name = item.get('persona_name', item.get('keycloak_user_id', 'N/A'))
                            print(f"      - {name}")
            
            if updated:
                print(f"   📝 Actualizados: {len(updated)}")
                if len(updated) <= 10:
                    for item in updated:
                        if isinstance(item, dict):
                            name = item.get('persona_name', item.get('keycloak_user_id', 'N/A'))
                            print(f"      - {name}")
            
            if synchronized:
                print(f"   🔄 Sincronizados: {len(synchronized)}")
                if len(synchronized) <= 10:
                    for item in synchronized:
                        if isinstance(item, dict):
                            print(f"      - ID: {item.get('persona_id', 'N/A')}")
            
            if removed:
                print(f"   🗑️  Eliminados: {len(removed)}")
                if len(removed) <= 10:
                    for item in removed:
                        if isinstance(item, dict):
                            name = item.get('persona_name', 'N/A')
                            reason = item.get('reason', 'N/A')
                            print(f"      - {name} ({reason})")
            
            if errors:
                print(f"   ❌ Errores: {len(errors)}")
                for error in errors[:5]:  # Show first 5 errors
                    if isinstance(error, dict):
                        error_msg = error.get('error', str(error))
                        print(f"      - {error_msg}")
                if len(errors) > 5:
                    print(f"      ... y {len(errors) - 5} errores más")
    
    # Print general errors
    if 'errors' in results and results['errors']:
        print(f"\n❌ ERRORES GENERALES:")
        for error in results['errors']:
            print(f"   • {error}")


def main():
    parser = argparse.ArgumentParser(description='Sincronización Keycloak-Personas')
    
    # Operation modes
    parser.add_argument('--full-sync', action='store_true',
                       help='Ejecutar sincronización completa bidireccional')
    parser.add_argument('--personas-to-keycloak', action='store_true',
                       help='Sincronizar solo personas locales a Keycloak')
    parser.add_argument('--keycloak-to-personas', action='store_true',
                       help='Sincronizar solo usuarios de Keycloak a personas locales')
    parser.add_argument('--remove-orphaned', action='store_true',
                       help='Eliminar personas huérfanas (requiere --confirm)')
    parser.add_argument('--status', action='store_true',
                       help='Mostrar estado actual (simulación completa)')
    
    # Options
    parser.add_argument('--dry-run', action='store_true',
                       help='Solo simular, no hacer cambios reales')
    parser.add_argument('--confirm', action='store_true',
                       help='Confirmar operaciones destructivas (eliminar personas)')
    parser.add_argument('--json', action='store_true',
                       help='Salida en formato JSON')
    parser.add_argument('--quiet', action='store_true',
                       help='Modo silencioso (solo errores)')
    
    args = parser.parse_args()
    
    # Validate arguments
    operations = [args.full_sync, args.personas_to_keycloak, 
                 args.keycloak_to_personas, args.remove_orphaned, args.status]
    
    if sum(operations) == 0:
        print("❌ Error: Debe especificar una operación")
        print("Use --help para ver las opciones disponibles")
        sys.exit(1)
    
    if sum(operations) > 1:
        print("❌ Error: Solo puede especificar una operación a la vez")
        sys.exit(1)
    
    if args.remove_orphaned and not args.dry_run and not args.confirm:
        print("❌ Error: --remove-orphaned requiere --confirm para operaciones reales")
        sys.exit(1)
    
    # Create Flask app context
    app = create_app()
    
    with app.app_context():
        try:
            sync_service = get_sync_service()
            
            if not sync_service.keycloak_admin:
                print("❌ Error: Keycloak Admin client no disponible")
                sys.exit(1)
            
            # Execute the requested operation
            results = None
            operation_name = ""
            
            if args.status or args.full_sync:
                operation_name = "Estado Actual" if args.status else "Sincronización Completa"
                results = sync_service.sync_all(dry_run=args.dry_run or args.status)
                
            elif args.personas_to_keycloak:
                operation_name = "Personas → Keycloak"
                results = {
                    'success': True,
                    'dry_run': args.dry_run,
                    'timestamp': datetime.utcnow().isoformat(),
                    'results': sync_service.sync_personas_to_keycloak(dry_run=args.dry_run)
                }
                
            elif args.keycloak_to_personas:
                operation_name = "Keycloak → Personas"
                results = {
                    'success': True,
                    'dry_run': args.dry_run,
                    'timestamp': datetime.utcnow().isoformat(),
                    'results': sync_service.sync_keycloak_to_personas(dry_run=args.dry_run)
                }
                
            elif args.remove_orphaned:
                operation_name = "Eliminar Personas Huérfanas"
                results = {
                    'success': True,
                    'dry_run': args.dry_run,
                    'timestamp': datetime.utcnow().isoformat(),
                    'results': sync_service.remove_orphaned_personas(dry_run=args.dry_run)
                }
            
            # Output results
            if args.json:
                print(json.dumps(results, indent=2, ensure_ascii=False))
            elif not args.quiet:
                print_results(results, operation_name)
            
            # Exit with error code if operation failed
            if not results.get('success', False):
                sys.exit(1)
                
        except KeyboardInterrupt:
            print("\n⚠️  Operación cancelada por el usuario")
            sys.exit(1)
        except Exception as e:
            error_msg = f"Error inesperado: {str(e)}"
            if args.json:
                print(json.dumps({
                    'success': False,
                    'error': error_msg,
                    'timestamp': datetime.utcnow().isoformat()
                }, indent=2, ensure_ascii=False))
            else:
                print(f"❌ {error_msg}")
            sys.exit(1)


if __name__ == '__main__':
    main()
