from app import create_app, init_app_data

app = create_app()
init_app_data(app)

if __name__ == '__main__':
    app.run(debug=True)