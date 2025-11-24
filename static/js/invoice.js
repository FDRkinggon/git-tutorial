// Gestion dynamique des lignes de facture

let lineCounter = 0;
let products = [];

// Charger les produits au démarrage
fetch('/api/products')
    .then(response => response.json())
    .then(data => {
        products = data;
    });

function addInvoiceLine() {
    const container = document.getElementById('invoiceLines');
    const lineId = lineCounter++;
    
    const lineHtml = `
        <div class="invoice-line" id="line_${lineId}">
            <div class="row">
                <div class="col-md-5">
                    <label class="form-label">Description *</label>
                    <input type="text" class="form-control" name="item_description_${lineId}" 
                           id="desc_${lineId}" required>
                    <select class="form-select form-select-sm mt-1" onchange="selectProduct(${lineId}, this.value)">
                        <option value="">-- Ou choisir un produit --</option>
                        ${products.map(p => `<option value="${p.id}">${p.name} - ${p.price}€</option>`).join('')}
                    </select>
                </div>
                <div class="col-md-2">
                    <label class="form-label">Quantité *</label>
                    <input type="number" step="0.01" class="form-control" 
                           name="item_quantity_${lineId}" id="qty_${lineId}" 
                           value="1" min="0.01" required onchange="calculateLine(${lineId})">
                </div>
                <div class="col-md-2">
                    <label class="form-label">Prix HT *</label>
                    <input type="number" step="0.01" class="form-control" 
                           name="item_price_${lineId}" id="price_${lineId}" 
                           value="0" min="0" required onchange="calculateLine(${lineId})">
                </div>
                <div class="col-md-2">
                    <label class="form-label">TVA %</label>
                    <select class="form-select" name="item_tva_${lineId}" 
                            id="tva_${lineId}" onchange="calculateLine(${lineId})">
                        <option value="0">0%</option>
                        <option value="5.5">5.5%</option>
                        <option value="10">10%</option>
                        <option value="20" selected>20%</option>
                    </select>
                </div>
                <div class="col-md-1 d-flex align-items-end">
                    <button type="button" class="btn btn-danger btn-sm w-100" 
                            onclick="removeLine(${lineId})">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
            </div>
            <input type="hidden" name="item_unit_${lineId}" id="unit_${lineId}" value="unité">
            <div class="mt-2">
                <small class="text-muted">Total ligne: <strong><span id="line_total_${lineId}">0.00</span> € HT</strong></small>
            </div>
        </div>
    `;
    
    container.insertAdjacentHTML('beforeend', lineHtml);
    document.getElementById('items_count').value = lineCounter;
}

function removeLine(lineId) {
    const line = document.getElementById(`line_${lineId}`);
    if (line) {
        line.remove();
        calculateTotals();
    }
}

function selectProduct(lineId, productId) {
    if (!productId) return;
    
    const product = products.find(p => p.id == productId);
    if (product) {
        document.getElementById(`desc_${lineId}`).value = product.name;
        document.getElementById(`price_${lineId}`).value = product.price;
        document.getElementById(`tva_${lineId}`).value = product.tva_rate;
        document.getElementById(`unit_${lineId}`).value = product.unit;
        calculateLine(lineId);
    }
}

function calculateLine(lineId) {
    const qty = parseFloat(document.getElementById(`qty_${lineId}`).value) || 0;
    const price = parseFloat(document.getElementById(`price_${lineId}`).value) || 0;
    const total = qty * price;
    
    document.getElementById(`line_total_${lineId}`).textContent = total.toFixed(2);
    calculateTotals();
}

function calculateTotals() {
    let subtotal = 0;
    let taxAmount = 0;
    
    // Parcourir toutes les lignes
    for (let i = 0; i < lineCounter; i++) {
        const qtyInput = document.getElementById(`qty_${i}`);
        const priceInput = document.getElementById(`price_${i}`);
        const tvaInput = document.getElementById(`tva_${i}`);
        
        if (qtyInput && priceInput && tvaInput) {
            const qty = parseFloat(qtyInput.value) || 0;
            const price = parseFloat(priceInput.value) || 0;
            const tva = parseFloat(tvaInput.value) || 0;
            
            const lineTotal = qty * price;
            subtotal += lineTotal;
            taxAmount += lineTotal * (tva / 100);
        }
    }
    
    // Appliquer la remise
    const discountType = document.getElementById('discount_type')?.value || 'none';
    const discountValue = parseFloat(document.getElementById('discount_value')?.value) || 0;
    
    let discountAmount = 0;
    if (discountType === 'percent') {
        discountAmount = subtotal * (discountValue / 100);
    } else if (discountType === 'amount') {
        discountAmount = discountValue;
    }
    
    const subtotalAfterDiscount = subtotal - discountAmount;
    const adjustedTax = subtotal > 0 ? taxAmount * (subtotalAfterDiscount / subtotal) : 0;
    const total = subtotalAfterDiscount + adjustedTax;
    
    // Afficher les totaux
    document.getElementById('subtotal').textContent = subtotal.toFixed(2);
    document.getElementById('tax').textContent = adjustedTax.toFixed(2);
    document.getElementById('total').textContent = total.toFixed(2);
}

// Recalculer lors du changement de remise
document.addEventListener('DOMContentLoaded', function() {
    const discountType = document.getElementById('discount_type');
    const discountValue = document.getElementById('discount_value');
    
    if (discountType) {
        discountType.addEventListener('change', calculateTotals);
    }
    if (discountValue) {
        discountValue.addEventListener('input', calculateTotals);
    }
});
