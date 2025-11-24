from app import create_app, db
from app.models import User, Client, Product, Invoice, InvoiceItem
app = create_app()
@app.shell_context_processor
def make_shell_context():
    return {
        'db': db,
        'User': User,
        'Client': Client,
        'Product': Product,
        'Invoice': Invoice,
        'InvoiceItem': InvoiceItem
    }
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)