from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, create_access_token
from sqlalchemy.exc import IntegrityError
from models import db, bcrypt, User, Book, Loan
from utils import validate_password
from datetime import datetime

app = Flask(__name__)
app.config.from_object('config.Config')

db.init_app(app)
bcrypt.init_app(app)
jwt = JWTManager(app)

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if not validate_password(password):
        return jsonify({'message': 'La contraseña no cumple con los requerimientos solicitados'}), 400

    new_user = User(username=username, email=email)
    new_user.set_password(password)

    try:
        db.session.add(new_user)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({'message': 'El usuario y/o correo ya existe'}), 409

    return jsonify({'message': 'Usuario registrado correctamente'}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    identifier = data.get('identifier')
    password = data.get('password')

    user = User.query.filter((User.username == identifier) | (User.email == identifier)).first()

    if user and user.check_password(password):
        access_token = create_access_token(identity=user.id)
        return jsonify({'message': 'Usuario logueado correctamente', 'access_token': access_token}), 200

    return jsonify({'message': 'Credenciales inválidas'}), 401

@app.route('/books', methods=['POST'])
def add_book():
    data = request.get_json()
    # Verificar si el libro ya existe
    if Book.query.filter_by(isbn=data.get('isbn')).first():
        return jsonify({'message': 'El libro con este ISBN ya existe'}), 409
    if Book.query.filter_by(title=data.get('title')).first():
        return jsonify({'message': 'Ya existe un libro con este título'}), 409

    new_book = Book(**data)
    db.session.add(new_book)
    db.session.commit()
    return jsonify({'message': 'Libro añadido correctamente'}), 201

@app.route('/books', methods=['GET'])
def get_books():
    books = Book.query.all()
    return jsonify([book.to_dict() for book in books]), 200

@app.route('/books/<int:book_id>', methods=['GET'])
def get_book(book_id):
    book = Book.query.get(book_id)
    if not book:
        return jsonify({'message': 'Libro no encontrado'}), 404
    return jsonify(book.to_dict()), 200

@app.route('/books/<int:book_id>', methods=['PUT'])
def update_book(book_id):
    data = request.get_json()
    book = Book.query.get(book_id)
    if not book:
        return jsonify({'message': 'Libro no encontrado'}), 404

    try:
        for key, value in data.items():
            setattr(book, key, value)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Error al actualizar el libro', 'error': str(e)}), 500

    return jsonify({'message': 'Libro actualizado correctamente'}), 200

@app.route('/books/<int:book_id>', methods=['DELETE'])
def delete_book(book_id):
    book = Book.query.get(book_id)
    if not book:
        return jsonify({'message': 'Libro no encontrado'}), 404

    try:
        db.session.delete(book)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Error al eliminar el libro', 'error': str(e)}), 500

    return jsonify({'message': 'Libro eliminado correctamente'}), 200

@app.route('/loans', methods=['POST'])
def create_loan():
    data = request.get_json()
    book_id = data.get('book_id')
    user_id = data.get('user_id')
    loan_date = data.get('loan_date')
    return_date = data.get('return_date')

    if not book_id or not user_id or not loan_date:
        return jsonify({'message': 'Faltan campos obligatorios'}), 400

    try:
        loan_date = datetime.fromisoformat(loan_date)
        return_date = datetime.fromisoformat(return_date) if return_date else None
    except ValueError:
        return jsonify({'message': 'Formato de fecha inválido'}), 400

    book = Book.query.get(book_id)
    user = User.query.get(user_id)

    if not book:
        return jsonify({'message': 'Libro no encontrado para su préstamo'}), 404
    if not user:
        return jsonify({'message': 'Usuario no encontrado'}), 404

    # Verificar el stock
    if book.stock <= 0:
        return jsonify({'message': 'Libro no disponible en stock'}), 400

    new_loan = Loan(book_id=book_id, user_id=user_id, loan_date=loan_date, return_date=return_date)
    try:
        db.session.add(new_loan)
        book.stock -= 1  # Reducir el stock
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Error al realizar el préstamo', 'error': str(e)}), 500

    return jsonify({'message': 'Préstamo realizado correctamente'}), 201

@app.route('/loans', methods=['GET'])
def get_loans():
    loans = Loan.query.all()
    return jsonify([{
        'id': loan.id,
        'book_id': loan.book_id,
        'user_id': loan.user_id,
        'loan_date': loan.loan_date.isoformat(),
        'return_date': loan.return_date.isoformat() if loan.return_date else None
    } for loan in loans]), 200

@app.route('/loans/<int:loan_id>', methods=['GET'])
def get_loan(loan_id):
    loan = Loan.query.get(loan_id)
    if not loan:
        return jsonify({'message': 'Préstamo no encontrado'}), 404
    return jsonify({
        'id': loan.id,
        'book_id': loan.book_id,
        'user_id': loan.user_id,
        'loan_date': loan.loan_date.isoformat(),
        'return_date': loan.return_date.isoformat() if loan.return_date else None
    }), 200

@app.route('/loans/<int:loan_id>', methods=['PUT'])
def update_loan(loan_id):
    data = request.get_json()
    return_date = data.get('return_date')

    loan = Loan.query.get(loan_id)
    if not loan:
        return jsonify({'message': 'Préstamo no encontrado'}), 404

    try:
        if return_date:
            loan.return_date = datetime.fromisoformat(return_date)
        else:
            loan.return_date = None

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Error al actualizar el préstamo', 'error': str(e)}), 500

    return jsonify({'message': 'Préstamo actualizado correctamente'}), 200

@app.route('/loans/<int:loan_id>', methods=['DELETE'])
def delete_loan(loan_id):
    loan = Loan.query.get(loan_id)
    if not loan:
        return jsonify({'message': 'Préstamo no encontrado'}), 404

    try:
        db.session.delete(loan)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Error al eliminar el préstamo', 'error': str(e)}), 500

    return jsonify({'message': 'Préstamo eliminado correctamente'}), 200

@app.route('/users', methods=['GET'])
def get_users():
    users = User.query.all()
    return jsonify([{
        'id': user.id,
        'username': user.username,
        'email': user.email
    } for user in users]), 200
