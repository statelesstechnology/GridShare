from flask import Flask
from .config import Config
from .models import db
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    migrate = Migrate(app, db)
    jwt = JWTManager(app)

    # Register blueprints
    from .routes.auth import auth_bp
    from .routes.scenario import scenario_bp
    from .routes.simulation import simulation_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(scenario_bp, url_prefix='/api/scenario')
    app.register_blueprint(simulation_bp, url_prefix='/api/simulation')

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)