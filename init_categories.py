from app import create_app
from app.models.models import db, Categoria, init_categories_from_json
import json

def main():
    # First, clear existing categories
    app = create_app()
    with app.app_context():
        print("Deleting existing categories...")
        db.session.query(Categoria).delete()
        db.session.commit()
        print("Existing categories deleted.")

        # Now load and initialize new categories
        print("Loading categories from roles_categorias.json...")
        with open('roles_categorias.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print("Initializing new categories...")
        init_categories_from_json(app, data)
        print("Categories initialized successfully!")

if __name__ == '__main__':
    main()