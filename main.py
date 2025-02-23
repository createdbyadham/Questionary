from api import create_app, db

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        # Drop all tables and recreate them
        db.drop_all()
        db.create_all()
        print("Database tables created successfully!")
    app.run(host='0.0.0.0', port=5001, debug=True)
