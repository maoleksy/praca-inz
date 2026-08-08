from database import db

class Size(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    size = db.Column(db.String(10), nullable=False)
    last_status = db.Column(db.String(20))

    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
