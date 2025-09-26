# Sistema de Concursos Docentes

## Descripción
Sistema para la gestión y seguimiento de concursos docentes universitarios.

## Documentación Ampliada
La documentación detallada del sistema ahora se encuentra en la carpeta `docs/`.

Contenido principal:
- Arquitectura: `docs/ARCHITECTURE_OVERVIEW.md`
- Modelos de Datos: `docs/MODELS.md`
- Rutas / Endpoints: `docs/ROUTES.md`
- Servicios internos: `docs/SERVICES.md`
- Integraciones externas (Keycloak / Google Drive): `docs/INTEGRATIONS.md`
- Generación de Documentos: `docs/DOCUMENT_GENERATION.md`
- Sistema de Placeholders: `docs/PLACEHOLDER_SYSTEM.md`
- Estrategia de Testing: `docs/TESTING.md`
- Guía de Refactorización: `docs/REFACTORING_GUIDE.md`
- Guía para Contribuciones Asistidas por IA: `docs/AI_CONTRIBUTION_GUIDE.md`
- Backlog de Deuda Técnica: `docs/TECH_DEBT_TODO.md`

Para cualquier cambio significativo, actualice los archivos relevantes y añada enlaces cruzados cuando corresponda.

## Changelog
Consulte `CHANGELOG.md` para un historial estructurado de cambios. Las nuevas entradas deben seguir el formato *Keep a Changelog* y Semantic Versioning.

## Nuevas Características

### Control de Estado y Subestado en Documentos

Se ha implementado un sistema avanzado para controlar el estado y subestado de los concursos a través de las plantillas de documentos:

1. **Subestado en Concursos**: Los concursos ahora tienen un campo `subestado` que puede acumular múltiples valores durante el flujo de trabajo.

2. **Configuración en Plantillas**: Las plantillas de documentos pueden definir:
   - `estado_al_generar_borrador`: Estado que se aplicará al concurso cuando se genere un borrador
   - `subestado_al_generar_borrador`: Valor que se añadirá al subestado cuando se genere un borrador
   - `estado_al_subir_firmado`: Estado que se aplicará al concurso cuando se suba el documento firmado
   - `subestado_al_subir_firmado`: Valor que se añadirá al subestado cuando se suba el documento firmado

3. **Comportamiento**:
   - Si estos valores se dejan vacíos en la plantilla, el estado y subestado permanecen intactos
   - Al eliminar documentos, se revierten automáticamente los cambios de estado y subestado
   - El subestado mantiene un historial acumulado de valores en formato JSON

4. **Gestión**:
   - Los valores de subestado se pueden añadir o eliminar dinámicamente según se generan o eliminan documentos
   - Permite un seguimiento detallado del progreso de cada concurso a través de sus documentos

## Instalación

1. Clonar el repositorio
2. Instalar dependencias: `pip install -r requirements.txt`
3. Configurar variables de entorno en `.env`
4. Inicializar la base de datos: `flask db upgrade`
5. Inicializar categorías: `flask init-categories`
6. Inicializar departamentos: `flask init-departments`
7. Inicializar plantillas: `flask init-templates`
8. Ejecutar el servidor: `flask run`

## Migración para nuevas características

Para aplicar las nuevas características de estado y subestado, ejecute:

```
flask db upgrade
```

## Configuración

Configure las siguientes variables en el archivo `.env`:

```
# Database configuration
DATABASE_URL=sqlite:///instance/concursos.db

# Authentication
SECRET_KEY=your-secret-key-here
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123

# Google Drive integration
GOOGLE_DRIVE_SECURE_TOKEN=your-secure-token
GOOGLE_DRIVE_ROOT_FOLDER=your-google-drive-root-folder-id

# Flask configuration
FLASK_APP=run.py
FLASK_ENV=development
```

## Roadmap y Deuda Técnica
Consulte `docs/TECH_DEBT_TODO.md` para el estado actualizado de tareas de mejora y refactorización. Para contribuciones nuevas siga las pautas en `docs/AI_CONTRIBUTION_GUIDE.md`.

## Contribuciones Asistidas por IA
Un agente de IA debe:
1. Añadir o reforzar tests antes de modificar lógica crítica.
2. Mantener las rutas delgadas moviendo lógica a servicios.
3. Registrar cambios estructurales en la guía de refactorización.
4. Actualizar documentación y backlog tras cada PR.

## Licencia
Pendiente de definir / agregar (añadir LICENSE si corresponde).
