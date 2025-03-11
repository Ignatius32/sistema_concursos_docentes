from app import create_app
from app.models.models import db, Departamento, Area, Orientacion
import json

def main():
    # First, clear existing data
    app = create_app()
    with app.app_context():
        print("Deleting existing departments, areas, and orientations...")
        # Delete in correct order due to foreign key constraints
        Orientacion.query.delete()
        Area.query.delete()
        Departamento.query.delete()
        db.session.commit()
        print("Existing data deleted.")

        # Now load and initialize new data
        print("Loading data from deptos_area_orientacion.json...")
        with open('deptos_area_orientacion.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Create departments, areas and orientations
        departments_created = {}
        areas_created = {}
        
        for dept_name, dept_data in data.items():
            # Create department
            dept = Departamento(nombre=dept_name)
            db.session.add(dept)
            db.session.flush()  # To get the ID
            departments_created[dept_name] = dept.id
            
            # Create areas and orientations
            for area_name, orientations in dept_data.items():
                area = Area(nombre=area_name, departamento_id=dept.id)
                db.session.add(area)
                db.session.flush()  # To get the ID
                
                # Create orientations
                for orientation_name in orientations:
                    if orientation_name:  # Skip empty orientation names
                        orientacion = Orientacion(nombre=orientation_name, area_id=area.id)
                        db.session.add(orientacion)
        
        db.session.commit()
        print("Departments, areas, and orientations initialized successfully!")

if __name__ == '__main__':
    main()