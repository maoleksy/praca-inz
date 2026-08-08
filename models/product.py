from database import db

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(200))
    slug = db.Column(db.String(200))

    sizes = db.relationship("Size", backref="product", cascade="all, delete")
