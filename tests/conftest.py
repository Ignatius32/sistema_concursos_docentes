"""
This file contains test initialization and shared fixtures.
"""
import sys
import os
import pytest
from datetime import datetime

# Add the application root directory to Python path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.models.models import db as _db
from app.models.models import Concurso, Departamento, Area, TribunalMiembro, Persona, Categoria, Postulante, Sustanciacion

@pytest.fixture(scope='session')
def app():
    """Create and configure a Flask app for testing."""
    app = create_app()  # Create the app with default configuration
    
    # Override configuration for testing
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    # Setup the app context
    with app.app_context():
        yield app

@pytest.fixture(scope='session')
def db(app):
    """Create a database for testing."""
    with app.app_context():
        _db.create_all()
        yield _db
        _db.drop_all()

@pytest.fixture(scope='function')
def session(db):
    """Create a new database session for a test."""
    connection = db.engine.connect()
    transaction = connection.begin()
    
    # Create a session bound to the connection
    session = db.session
    
    yield session
    
    # Rollback the transaction and restore the original session
    transaction.rollback()
    connection.close()

@pytest.fixture
def test_departamento(session):
    """Create a test departamento."""
    departamento = Departamento(
        nombre="Departamento de Prueba"
    )
    session.add(departamento)
    session.commit()
    return departamento

@pytest.fixture
def test_area(session, test_departamento):
    """Create a test area."""
    area = Area(
        nombre="Área de Prueba",
        departamento_id=test_departamento.id
    )
    session.add(area)
    session.commit()
    return area

@pytest.fixture
def test_categoria(session):
    """Create a test categoria."""
    categoria = Categoria(
        codigo="PAD",
        nombre="Profesor Adjunto",
        rol="Profesor"
    )
    session.add(categoria)
    session.commit()
    return categoria

@pytest.fixture
def test_persona(session):
    """Create a test persona."""
    import random
    # Create a random DNI to avoid unique constraint violations
    random_dni = f"3{random.randint(1000000, 9999999)}"
    
    persona = Persona(
        dni=random_dni,
        nombre="Test",
        apellido="Usuario",
        correo="test@example.com",
        telefono="1234567890"
    )
    session.add(persona)
    session.commit()
    return persona

@pytest.fixture
def test_concurso(session, test_departamento, test_categoria):
    """Create a test concurso."""
    concurso = Concurso(
        tipo="Regular",
        cerrado_abierto="Abierto",
        cant_cargos=1,
        departamento_id=test_departamento.id,
        area="Área de Prueba",
        orientacion="Orientación de Prueba",
        categoria=test_categoria.codigo,
        categoria_nombre=test_categoria.nombre,
        dedicacion="Simple",
        expediente="TEST-123/2025",
        origen_vacante="RENUNCIA",
        docente_vacante="Dr. Ejemplo Anterior",
        cierre_inscripcion=datetime.now().date()
    )
    session.add(concurso)
    session.commit()
    return concurso

@pytest.fixture
def test_tribunal_miembros(session, test_concurso, test_persona):
    """Create test tribunal members."""
    presidente = Persona(
        dni="30111111",
        nombre="Presidente",
        apellido="Tribunal",
        correo="presidente@example.com"
    )
    vocal = Persona(
        dni="30222222",
        nombre="Vocal",
        apellido="Tribunal",
        correo="vocal@example.com"
    )
    suplente = Persona(
        dni="30333333",
        nombre="Suplente",
        apellido="Tribunal",
        correo="suplente@example.com"
    )
    
    session.add_all([presidente, vocal, suplente])
    session.commit()
    
    # Create tribunal assignments
    presidente_asignacion = TribunalMiembro(
        concurso_id=test_concurso.id,
        persona_id=presidente.id,
        rol="Presidente",
        claustro="Docente"
    )
    
    vocal_asignacion = TribunalMiembro(
        concurso_id=test_concurso.id,
        persona_id=vocal.id,
        rol="Titular",
        claustro="Docente"
    )
    
    suplente_asignacion = TribunalMiembro(
        concurso_id=test_concurso.id,
        persona_id=suplente.id,
        rol="Suplente",
        claustro="Docente"
    )
    
    session.add_all([presidente_asignacion, vocal_asignacion, suplente_asignacion])
    session.commit()
    
    return [presidente_asignacion, vocal_asignacion, suplente_asignacion]

@pytest.fixture
def test_postulantes(session, test_concurso):
    """Create test postulantes."""
    postulante1 = Postulante(
        concurso_id=test_concurso.id,
        dni="35111111",
        nombre="Postulante1",
        apellido="Apellido1",
        correo="postulante1@example.com",
        excluido=False
    )
    
    postulante2 = Postulante(
        concurso_id=test_concurso.id,
        dni="35222222",
        nombre="Postulante2",
        apellido="Apellido2",
        correo="postulante2@example.com",
        excluido=False
    )
    
    session.add_all([postulante1, postulante2])
    session.commit()
    
    return [postulante1, postulante2]

@pytest.fixture
def test_sustanciacion(session, test_concurso):
    """Create test sustanciacion data."""
    sustanciacion = Sustanciacion(
        concurso_id=test_concurso.id,
        fecha_constitucion=datetime.now().date(),
        lugar_constitucion="Sala de Reuniones",
        link_virtual_constitucion="https://meet.example.com/constitucion",
        fecha_sorteo=datetime.now().date(),
        lugar_sorteo="Sala de Reuniones",
        link_virtual_sorteo="https://meet.example.com/sorteo",
        fecha_clase=datetime.now().date(),
        lugar_clase="Aula 101",
        link_virtual_clase="https://meet.example.com/clase",
        temas_exposicion="Tema 1|Tema 2|Tema 3"
    )
    
    session.add(sustanciacion)
    session.commit()
    
    return sustanciacion
