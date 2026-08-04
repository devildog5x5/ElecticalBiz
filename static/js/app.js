import { renderReports as renderReportsPage } from './reports.js';
import { renderReminders as renderRemindersPage } from './reminders.js';

const TABS = [
  { id: 'dashboard', label: '📊  DASHBOARD', subtitle: 'Business overview' },
  { id: 'suppliers', label: '🏭  SUPPLIERS', subtitle: 'Wholesalers & manufacturers' },
  { id: 'products', label: '📦  PRODUCTS', subtitle: 'Product catalog' },
  { id: 'purchase-orders', label: '🛒  PURCHASE ORDERS', subtitle: 'Buying from suppliers' },
  { id: 'inventory', label: '🏪  INVENTORY', subtitle: 'Stock levels & receiving' },
  { id: 'customers', label: '👷  CUSTOMERS', subtitle: 'Contractors & builders' },
  { id: 'jobs', label: '🏗️  JOBS', subtitle: 'Project tracking' },
  { id: 'quotes', label: '📝  QUOTES', subtitle: 'Estimates & proposals' },
  { id: 'sales-orders', label: '🚚  SALES ORDERS', subtitle: 'Customer orders' },
  { id: 'invoices', label: '💰  INVOICES', subtitle: 'Billing & payments' },
  { id: 'reminders', label: '🔔  REMINDERS', subtitle: 'Email tasks & notifications' },
  { id: 'reports', label: '📈  REPORTS', subtitle: 'Analytics & margins' },
];

let currentPage = 'dashboard';
let cache = {};

const $ = (sel) => document.querySelector(sel);
const content = () => $('#content');
const topbarActions = () => $('#topbar-actions');

function fmt(n) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(n || 0);
}

function fmtDate(d) {
  if (!d) return '—';
  return new Date(d + 'T00:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function badge(status) {
  return `<span class="badge badge-${status}">${status.replace('_', ' ')}</span>`;
}

async function api(path, opts = {}) {
  const res = await fetch(`/api/${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || `Request failed (${res.status})`);
  }
  if (res.status === 204) return null;
  return res.json();
}

function toast(msg) {
  const el = document.createElement('div');
  el.className = 'toast';
  el.textContent = msg;
  $('#toast-container').appendChild(el);
  setTimeout(() => el.remove(), 3500);
}

function showModal(title, bodyHtml, footerHtml) {
  $('#modal-title').textContent = title;
  $('#modal-body').innerHTML = bodyHtml;
  $('#modal-footer').innerHTML = footerHtml || '';
  $('#modal-overlay').classList.remove('hidden');
}

function hideModal() {
  $('#modal-overlay').classList.add('hidden');
}

$('#modal-close').onclick = hideModal;
$('#modal-overlay').onclick = (e) => { if (e.target === $('#modal-overlay')) hideModal(); };

function renderNav() {
  const bar = $('#tab-bar');
  bar.innerHTML = TABS.map(tab => `
    <button class="tab-item ${tab.id === currentPage ? 'active' : ''}" data-page="${tab.id}">${tab.label}</button>
  `).join('');
  bar.querySelectorAll('.tab-item').forEach(btn => {
    btn.onclick = () => navigate(btn.dataset.page);
  });
}

function navigate(page) {
  currentPage = page;
  const tab = TABS.find(t => t.id === page);
  const title = tab.label.replace(/^[^\s]+\s+/, '').replace(/\s+/g, ' ');
  $('#page-title').textContent = title.charAt(0) + title.slice(1).toLowerCase();
  $('#page-subtitle').textContent = tab.subtitle;
  renderNav();
  const pages = {
    dashboard: renderDashboard,
    suppliers: renderSuppliers,
    products: renderProducts,
    'purchase-orders': renderPurchaseOrders,
    inventory: renderInventory,
    customers: renderCustomers,
    jobs: renderJobs,
    quotes: renderQuotes,
    'sales-orders': renderSalesOrders,
    invoices: renderInvoices,
    reminders: renderReminders,
    reports: renderReports,
  };
  pages[page]?.();
}

// --- Dashboard ---

async function renderDashboard() {
  topbarActions().innerHTML = '';
  content().innerHTML = '<div class="text-muted">Loading...</div>';
  const d = await api('dashboard');

  content().innerHTML = `
    <div class="hero-banner">
      <h2><img class="hero-icon" src="/static/img/icon.png" alt=""> Electrical Supply Dashboard</h2>
      <p>Complete overview of purchasing, inventory, sales, and billing</p>
    </div>

    <div class="metric-grid mb-20">
      <div class="metric-card">
        <div class="metric-label">💵 Revenue (MTD)</div>
        <div class="metric-value gold">${fmt(d.revenue_mtd)}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">📋 Outstanding A/R</div>
        <div class="metric-value red">${fmt(d.outstanding_ar)}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">🏪 Inventory Value</div>
        <div class="metric-value green">${fmt(d.inventory_value)}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">⚠️ Low Stock Items</div>
        <div class="metric-value amber">${d.low_stock.length}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">🛒 Open Purchase Orders</div>
        <div class="metric-value blue">${d.open_pos}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">🚚 Open Sales Orders</div>
        <div class="metric-value blue">${d.open_orders}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">🏗️ Active Jobs</div>
        <div class="metric-value purple">${d.active_jobs}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">📝 Pending Quotes</div>
        <div class="metric-value amber">${d.pending_quotes}</div>
      </div>
    </div>

    <div class="grid grid-2 mb-20">
      <div class="card">
        <div class="card-header"><div class="card-title">Low Stock Alerts</div></div>
        ${d.low_stock.length ? `
          <div class="table-wrap"><table>
            <thead><tr><th>SKU</th><th>Product</th><th>On Hand</th><th>Reorder</th></tr></thead>
            <tbody>${d.low_stock.map(i => `
              <tr><td>${i.sku}</td><td>${i.name}</td>
              <td class="low-stock">${i.quantity_on_hand}</td><td>${i.reorder_level}</td></tr>
            `).join('')}</tbody>
          </table></div>
        ` : '<div class="empty-state"><div class="empty-icon">✅</div>All stock levels healthy</div>'}
      </div>
      <div class="card">
        <div class="card-header"><div class="card-title">Recent Activity</div></div>
        ${d.recent_activity.map(a => `
          <div class="activity-item">
            <div class="activity-dot"></div>
            <div>
              <div class="activity-text">${a.description}</div>
              <div class="activity-time">${a.created_at}</div>
            </div>
          </div>
        `).join('')}
      </div>
    </div>

    <div class="tips-card">
      <h3>💡 Supply Chain Tips</h3>
      <ul>
        <li>Review low-stock alerts daily and reorder before job site delays</li>
        <li>Send POs to preferred wholesalers for volume pricing on wire and conduit</li>
        <li>Link sales orders to jobs for accurate contractor billing</li>
        <li>Convert accepted quotes directly to sales orders to avoid re-entry</li>
        <li>Receive inventory promptly — update stock when shipments arrive</li>
        <li>Track outstanding A/R weekly and follow up before terms expire</li>
        <li>Use margin reports to adjust pricing on high-volume SKUs</li>
      </ul>
    </div>
  `;
}

// --- Suppliers ---

async function renderSuppliers() {
  topbarActions().innerHTML = '<button class="btn btn-primary" id="add-supplier">+ Add Supplier</button>';
  content().innerHTML = '<div class="text-muted">Loading...</div>';
  const data = await api('suppliers');

  content().innerHTML = `
    <div class="card">
      <div class="table-wrap"><table>
        <thead><tr>
          <th>Name</th><th>Type</th><th>Contact</th><th>Phone</th><th>Account #</th><th>Terms</th><th></th>
        </tr></thead>
        <tbody>${data.map(s => `
          <tr>
            <td><strong>${s.name}</strong></td>
            <td>${badge(s.type)}</td>
            <td>${s.contact_name || '—'}<br><span class="text-muted">${s.email || ''}</span></td>
            <td>${s.phone || '—'}</td>
            <td>${s.account_number || '—'}</td>
            <td>${s.payment_terms}</td>
            <td><button class="btn btn-sm btn-secondary edit-supplier" data-id="${s.id}">Edit</button></td>
          </tr>
        `).join('')}</tbody>
      </table></div>
    </div>
  `;

  $('#add-supplier').onclick = () => showSupplierForm();
  document.querySelectorAll('.edit-supplier').forEach(btn => {
    btn.onclick = () => showSupplierForm(data.find(s => s.id == btn.dataset.id));
  });
}

function showSupplierForm(supplier = null) {
  const isEdit = !!supplier;
  showModal(isEdit ? 'Edit Supplier' : 'Add Supplier', `
    <form id="supplier-form" class="form-grid">
      <div class="form-group"><label>Name *</label><input name="name" required value="${supplier?.name || ''}"></div>
      <div class="form-group"><label>Type *</label>
        <select name="type" required>
          <option value="wholesaler" ${supplier?.type === 'wholesaler' ? 'selected' : ''}>Wholesaler</option>
          <option value="manufacturer" ${supplier?.type === 'manufacturer' ? 'selected' : ''}>Manufacturer</option>
        </select>
      </div>
      <div class="form-group"><label>Contact Name</label><input name="contact_name" value="${supplier?.contact_name || ''}"></div>
      <div class="form-group"><label>Email</label><input name="email" type="email" value="${supplier?.email || ''}"></div>
      <div class="form-group"><label>Phone</label><input name="phone" value="${supplier?.phone || ''}"></div>
      <div class="form-group"><label>Account Number</label><input name="account_number" value="${supplier?.account_number || ''}"></div>
      <div class="form-group full"><label>Address</label><input name="address" value="${supplier?.address || ''}"></div>
      <div class="form-group"><label>Payment Terms</label><input name="payment_terms" value="${supplier?.payment_terms || 'Net 30'}"></div>
      <div class="form-group full"><label>Notes</label><textarea name="notes">${supplier?.notes || ''}</textarea></div>
    </form>
  `, `<button class="btn btn-secondary" onclick="document.getElementById('modal-overlay').classList.add('hidden')">Cancel</button>
      <button class="btn btn-primary" id="save-supplier">Save</button>`);

  $('#save-supplier').onclick = async () => {
    const form = $('#supplier-form');
    const body = Object.fromEntries(new FormData(form));
    try {
      if (isEdit) await api(`suppliers/${supplier.id}`, { method: 'PUT', body });
      else await api('suppliers', { method: 'POST', body });
      hideModal(); toast(isEdit ? 'Supplier updated' : 'Supplier added'); renderSuppliers();
    } catch (e) { toast(e.message); }
  };
}

// --- Products ---

async function renderProducts() {
  topbarActions().innerHTML = '<button class="btn btn-primary" id="add-product">+ Add Product</button>';
  content().innerHTML = '<div class="text-muted">Loading...</div>';
  const data = await api('products');

  content().innerHTML = `
    <div class="card">
      <div class="table-wrap"><table>
        <thead><tr>
          <th>SKU</th><th>Name</th><th>Category</th><th>Cost</th><th>Price</th><th>Stock</th><th>Supplier</th><th></th>
        </tr></thead>
        <tbody>${data.map(p => `
          <tr>
            <td><code>${p.sku}</code></td>
            <td>${p.name}</td>
            <td>${p.category}</td>
            <td>${fmt(p.cost)}</td>
            <td>${fmt(p.price)}</td>
            <td class="${p.quantity_on_hand <= p.reorder_level ? 'low-stock' : ''}">${p.quantity_on_hand}</td>
            <td>${p.supplier_name || '—'}</td>
            <td><button class="btn btn-sm btn-secondary edit-product" data-id="${p.id}">Edit</button></td>
          </tr>
        `).join('')}</tbody>
      </table></div>
    </div>
  `;

  $('#add-product').onclick = () => showProductForm();
  document.querySelectorAll('.edit-product').forEach(btn => {
    btn.onclick = () => showProductForm(data.find(p => p.id == btn.dataset.id));
  });
}

async function showProductForm(product = null) {
  const suppliers = await api('suppliers');
  const isEdit = !!product;
  showModal(isEdit ? 'Edit Product' : 'Add Product', `
    <form id="product-form" class="form-grid">
      <div class="form-group"><label>SKU *</label><input name="sku" required value="${product?.sku || ''}"></div>
      <div class="form-group"><label>Name *</label><input name="name" required value="${product?.name || ''}"></div>
      <div class="form-group"><label>Category *</label>
        <select name="category" required>
          ${['Wire & Cable','Breakers','Panels','Conduit','Boxes & Fittings','Devices','Lighting','Other'].map(c =>
            `<option ${product?.category === c ? 'selected' : ''}>${c}</option>`).join('')}
        </select>
      </div>
      <div class="form-group"><label>Unit</label><input name="unit" value="${product?.unit || 'each'}"></div>
      <div class="form-group"><label>Cost</label><input name="cost" type="number" step="0.01" value="${product?.cost || 0}"></div>
      <div class="form-group"><label>Price</label><input name="price" type="number" step="0.01" value="${product?.price || 0}"></div>
      <div class="form-group"><label>Reorder Level</label><input name="reorder_level" type="number" value="${product?.reorder_level || 10}"></div>
      <div class="form-group"><label>Qty On Hand</label><input name="quantity_on_hand" type="number" value="${product?.quantity_on_hand || 0}"></div>
      <div class="form-group"><label>Supplier</label>
        <select name="supplier_id"><option value="">— None —</option>
          ${suppliers.map(s => `<option value="${s.id}" ${product?.supplier_id == s.id ? 'selected' : ''}>${s.name}</option>`).join('')}
        </select>
      </div>
      <div class="form-group"><label>Mfr Part #</label><input name="manufacturer_part" value="${product?.manufacturer_part || ''}"></div>
      <div class="form-group full"><label>Description</label><textarea name="description">${product?.description || ''}</textarea></div>
    </form>
  `, `<button class="btn btn-secondary" onclick="document.getElementById('modal-overlay').classList.add('hidden')">Cancel</button>
      <button class="btn btn-primary" id="save-product">Save</button>`);

  $('#save-product').onclick = async () => {
    const form = $('#product-form');
    const body = Object.fromEntries(new FormData(form));
    body.cost = parseFloat(body.cost); body.price = parseFloat(body.price);
    body.reorder_level = parseInt(body.reorder_level);
    body.quantity_on_hand = parseInt(body.quantity_on_hand);
    body.supplier_id = body.supplier_id ? parseInt(body.supplier_id) : null;
    try {
      if (isEdit) await api(`products/${product.id}`, { method: 'PUT', body });
      else await api('products', { method: 'POST', body });
      hideModal(); toast(isEdit ? 'Product updated' : 'Product added'); renderProducts();
    } catch (e) { toast(e.message); }
  };
}

// --- Purchase Orders ---

async function renderPurchaseOrders() {
  topbarActions().innerHTML = '<button class="btn btn-primary" id="add-po">+ New Purchase Order</button>';
  content().innerHTML = '<div class="text-muted">Loading...</div>';
  const data = await api('purchase-orders');

  content().innerHTML = `
    <div class="card">
      <div class="table-wrap"><table>
        <thead><tr>
          <th>PO #</th><th>Supplier</th><th>Date</th><th>Expected</th><th>Total</th><th>Status</th><th>Actions</th>
        </tr></thead>
        <tbody>${data.map(po => `
          <tr>
            <td><strong>${po.po_number}</strong></td>
            <td>${po.supplier_name}</td>
            <td>${fmtDate(po.order_date)}</td>
            <td>${fmtDate(po.expected_date)}</td>
            <td>${fmt(po.total)}</td>
            <td>${badge(po.status)}</td>
            <td class="gap-8">
              <button class="btn btn-sm btn-secondary view-po" data-id="${po.id}">View</button>
              ${po.status === 'sent' || po.status === 'partial' ? `<button class="btn btn-sm btn-primary receive-po" data-id="${po.id}">Receive</button>` : ''}
              ${po.status === 'draft' ? `<button class="btn btn-sm btn-primary send-po" data-id="${po.id}">Send</button>` : ''}
            </td>
          </tr>
        `).join('')}</tbody>
      </table></div>
    </div>
  `;

  $('#add-po').onclick = () => showPOForm();
  document.querySelectorAll('.view-po').forEach(btn => {
    btn.onclick = () => viewPO(data.find(p => p.id == btn.dataset.id));
  });
  document.querySelectorAll('.receive-po').forEach(btn => {
    btn.onclick = () => receivePO(data.find(p => p.id == btn.dataset.id));
  });
  document.querySelectorAll('.send-po').forEach(btn => {
    btn.onclick = async () => {
      await api(`purchase-orders/${btn.dataset.id}/status`, { method: 'PATCH', body: { status: 'sent' } });
      toast('PO sent to supplier'); renderPurchaseOrders();
    };
  });
}

function viewPO(po) {
  showModal(po.po_number, `
    <dl class="detail-grid">
      <dt>Supplier</dt><dd>${po.supplier_name}</dd>
      <dt>Status</dt><dd>${badge(po.status)}</dd>
      <dt>Order Date</dt><dd>${fmtDate(po.order_date)}</dd>
      <dt>Expected</dt><dd>${fmtDate(po.expected_date)}</dd>
      <dt>Subtotal</dt><dd>${fmt(po.subtotal)}</dd>
      <dt>Tax</dt><dd>${fmt(po.tax)}</dd>
      <dt>Total</dt><dd class="text-accent">${fmt(po.total)}</dd>
      <dt>Notes</dt><dd>${po.notes || '—'}</dd>
    </dl>
    <div class="mt-16 table-wrap"><table>
      <thead><tr><th>Product</th><th>Ordered</th><th>Received</th><th>Unit Cost</th><th>Total</th></tr></thead>
      <tbody>${po.lines.map(l => `
        <tr><td>${l.product_name}</td><td>${l.quantity_ordered}</td><td>${l.quantity_received}</td>
        <td>${fmt(l.unit_cost)}</td><td>${fmt(l.line_total)}</td></tr>
      `).join('')}</tbody>
    </table></div>
  `, '<button class="btn btn-secondary" onclick="document.getElementById(\'modal-overlay\').classList.add(\'hidden\')">Close</button>');
}

async function receivePO(po) {
  showModal(`Receive ${po.po_number}`, `
    <div class="table-wrap"><table>
      <thead><tr><th>Product</th><th>Ordered</th><th>Received</th><th>Receive Qty</th></tr></thead>
      <tbody>${po.lines.map(l => `
        <tr data-line-id="${l.id}">
          <td>${l.product_name}</td><td>${l.quantity_ordered}</td><td>${l.quantity_received}</td>
          <td><input type="number" class="recv-qty" min="0" max="${l.quantity_ordered - l.quantity_received}"
            value="${l.quantity_ordered - l.quantity_received}" style="width:80px"></td>
        </tr>
      `).join('')}</tbody>
    </table></div>
  `, `<button class="btn btn-secondary" onclick="document.getElementById('modal-overlay').classList.add('hidden')">Cancel</button>
      <button class="btn btn-primary" id="confirm-receive">Confirm Receipt</button>`);

  $('#confirm-receive').onclick = async () => {
    const lines = [...document.querySelectorAll('tr[data-line-id]')].map(tr => ({
      line_id: parseInt(tr.dataset.lineId),
      quantity: parseInt(tr.querySelector('.recv-qty').value) || 0,
    })).filter(l => l.quantity > 0);
    try {
      await api(`purchase-orders/${po.id}/receive`, { method: 'POST', body: { lines } });
      hideModal(); toast('Inventory updated'); renderPurchaseOrders();
    } catch (e) { toast(e.message); }
  };
}

async function showPOForm() {
  const [suppliers, products] = await Promise.all([api('suppliers'), api('products')]);
  showModal('New Purchase Order', `
    <form id="po-form">
      <div class="form-grid">
        <div class="form-group"><label>Supplier *</label>
          <select name="supplier_id" required>${suppliers.map(s => `<option value="${s.id}">${s.name}</option>`).join('')}</select>
        </div>
        <div class="form-group"><label>Expected Date</label><input name="expected_date" type="date"></div>
        <div class="form-group full"><label>Notes</label><textarea name="notes"></textarea></div>
      </div>
      <div class="line-items mt-16">
        <div class="line-items-header"><span>Product</span><span>Qty</span><span>Unit Cost</span><span>Total</span><span></span></div>
        <div id="po-lines"></div>
        <button type="button" class="btn btn-sm btn-secondary mt-16" id="add-po-line">+ Add Line</button>
      </div>
    </form>
  `, `<button class="btn btn-secondary" onclick="document.getElementById('modal-overlay').classList.add('hidden')">Cancel</button>
      <button class="btn btn-primary" id="save-po">Create PO</button>`);

  const linesEl = $('#po-lines');
  const productOpts = products.map(p => `<option value="${p.id}" data-cost="${p.cost}">${p.sku} — ${p.name}</option>`).join('');

  function addLine() {
    const row = document.createElement('div');
    row.className = 'line-item-row';
    row.innerHTML = `
      <select class="line-product">${productOpts}</select>
      <input type="number" class="line-qty" value="1" min="1">
      <input type="number" class="line-cost" step="0.01" value="${products[0]?.cost || 0}">
      <span class="line-total">${fmt(products[0]?.cost || 0)}</span>
      <button type="button" class="btn-icon remove-line">&times;</button>
    `;
    const update = () => {
      const qty = parseFloat(row.querySelector('.line-qty').value) || 0;
      const cost = parseFloat(row.querySelector('.line-cost').value) || 0;
      row.querySelector('.line-total').textContent = fmt(qty * cost);
    };
    row.querySelector('.line-product').onchange = (e) => {
      row.querySelector('.line-cost').value = e.target.selectedOptions[0].dataset.cost;
      update();
    };
    row.querySelector('.line-qty').oninput = update;
    row.querySelector('.line-cost').oninput = update;
    row.querySelector('.remove-line').onclick = () => row.remove();
    linesEl.appendChild(row);
  }
  addLine();
  $('#add-po-line').onclick = addLine;

  $('#save-po').onclick = async () => {
    const form = $('#po-form');
    const fd = Object.fromEntries(new FormData(form));
    const lines = [...linesEl.querySelectorAll('.line-item-row')].map(row => ({
      product_id: parseInt(row.querySelector('.line-product').value),
      quantity_ordered: parseInt(row.querySelector('.line-qty').value),
      unit_cost: parseFloat(row.querySelector('.line-cost').value),
    }));
    if (!lines.length) return toast('Add at least one line item');
    try {
      await api('purchase-orders', { method: 'POST', body: { supplier_id: parseInt(fd.supplier_id), expected_date: fd.expected_date, notes: fd.notes, lines } });
      hideModal(); toast('Purchase order created'); renderPurchaseOrders();
    } catch (e) { toast(e.message); }
  };
}

// --- Inventory ---

async function renderInventory() {
  topbarActions().innerHTML = '';
  content().innerHTML = '<div class="text-muted">Loading...</div>';
  const data = await api('inventory');
  const totalValue = data.reduce((s, i) => s + i.stock_value, 0);

  content().innerHTML = `
    <div class="metric-grid mb-20" style="grid-template-columns: repeat(3, 1fr);">
      <div class="metric-card"><div class="metric-label">Total SKUs</div><div class="metric-value blue">${data.length}</div></div>
      <div class="metric-card"><div class="metric-label">Total Units</div><div class="metric-value green">${data.reduce((s,i) => s + i.quantity_on_hand, 0).toLocaleString()}</div></div>
      <div class="metric-card"><div class="metric-label">Total Value</div><div class="metric-value gold">${fmt(totalValue)}</div></div>
    </div>
    <div class="card">
      <div class="table-wrap"><table>
        <thead><tr>
          <th>SKU</th><th>Product</th><th>Category</th><th>On Hand</th><th>Reserved</th><th>Available</th><th>Reorder</th><th>Value</th><th>Location</th>
        </tr></thead>
        <tbody>${data.map(i => `
          <tr class="${i.low_stock ? 'low-stock' : ''}">
            <td><code>${i.sku}</code></td><td>${i.name}</td><td>${i.category}</td>
            <td>${i.quantity_on_hand}</td><td>${i.quantity_reserved}</td>
            <td>${i.quantity_on_hand - i.quantity_reserved}</td>
            <td>${i.reorder_level}</td><td>${fmt(i.stock_value)}</td><td>${i.location}</td>
          </tr>
        `).join('')}</tbody>
      </table></div>
    </div>
  `;
}

// --- Customers ---

async function renderCustomers() {
  topbarActions().innerHTML = '<button class="btn btn-primary" id="add-customer">+ Add Customer</button>';
  content().innerHTML = '<div class="text-muted">Loading...</div>';
  const data = await api('customers');

  content().innerHTML = `
    <div class="card">
      <div class="table-wrap"><table>
        <thead><tr>
          <th>Name</th><th>Type</th><th>Contact</th><th>Phone</th><th>Credit Limit</th><th>Terms</th><th></th>
        </tr></thead>
        <tbody>${data.map(c => `
          <tr>
            <td><strong>${c.name}</strong></td>
            <td>${badge(c.type)}</td>
            <td>${c.contact_name || '—'}<br><span class="text-muted">${c.email || ''}</span></td>
            <td>${c.phone || '—'}</td>
            <td>${fmt(c.credit_limit)}</td>
            <td>${c.payment_terms}</td>
            <td><button class="btn btn-sm btn-secondary edit-customer" data-id="${c.id}">Edit</button></td>
          </tr>
        `).join('')}</tbody>
      </table></div>
    </div>
  `;

  $('#add-customer').onclick = () => showCustomerForm();
  document.querySelectorAll('.edit-customer').forEach(btn => {
    btn.onclick = () => showCustomerForm(data.find(c => c.id == btn.dataset.id));
  });
}

function showCustomerForm(customer = null) {
  const isEdit = !!customer;
  showModal(isEdit ? 'Edit Customer' : 'Add Customer', `
    <form id="customer-form" class="form-grid">
      <div class="form-group"><label>Name *</label><input name="name" required value="${customer?.name || ''}"></div>
      <div class="form-group"><label>Type *</label>
        <select name="type" required>
          ${['contractor','builder','commercial','residential'].map(t =>
            `<option value="${t}" ${customer?.type === t ? 'selected' : ''}>${t.charAt(0).toUpperCase()+t.slice(1)}</option>`).join('')}
        </select>
      </div>
      <div class="form-group"><label>Contact Name</label><input name="contact_name" value="${customer?.contact_name || ''}"></div>
      <div class="form-group"><label>Email</label><input name="email" type="email" value="${customer?.email || ''}"></div>
      <div class="form-group"><label>Phone</label><input name="phone" value="${customer?.phone || ''}"></div>
      <div class="form-group"><label>Credit Limit</label><input name="credit_limit" type="number" value="${customer?.credit_limit || 10000}"></div>
      <div class="form-group"><label>Payment Terms</label><input name="payment_terms" value="${customer?.payment_terms || 'Net 30'}"></div>
      <div class="form-group full"><label>Address</label><input name="address" value="${customer?.address || ''}"></div>
      <div class="form-group"><label><input type="checkbox" name="tax_exempt" ${customer?.tax_exempt ? 'checked' : ''}> Tax Exempt</label></div>
      <div class="form-group full"><label>Notes</label><textarea name="notes">${customer?.notes || ''}</textarea></div>
    </form>
  `, `<button class="btn btn-secondary" onclick="document.getElementById('modal-overlay').classList.add('hidden')">Cancel</button>
      <button class="btn btn-primary" id="save-customer">Save</button>`);

  $('#save-customer').onclick = async () => {
    const form = $('#customer-form');
    const body = Object.fromEntries(new FormData(form));
    body.tax_exempt = form.querySelector('[name=tax_exempt]').checked;
    body.credit_limit = parseFloat(body.credit_limit);
    try {
      if (isEdit) await api(`customers/${customer.id}`, { method: 'PUT', body });
      else await api('customers', { method: 'POST', body });
      hideModal(); toast(isEdit ? 'Customer updated' : 'Customer added'); renderCustomers();
    } catch (e) { toast(e.message); }
  };
}

// --- Jobs ---

async function renderJobs() {
  topbarActions().innerHTML = '<button class="btn btn-primary" id="add-job">+ New Job</button>';
  content().innerHTML = '<div class="text-muted">Loading...</div>';
  const data = await api('jobs');

  content().innerHTML = `
    <div class="card">
      <div class="table-wrap"><table>
        <thead><tr>
          <th>Job #</th><th>Name</th><th>Customer</th><th>Site</th><th>Value</th><th>Status</th><th>Dates</th>
        </tr></thead>
        <tbody>${data.map(j => `
          <tr>
            <td><strong>${j.job_number}</strong></td>
            <td>${j.name}</td>
            <td>${j.customer_name}</td>
            <td class="text-muted">${j.site_address || '—'}</td>
            <td>${fmt(j.estimated_value)}</td>
            <td>${badge(j.status)}</td>
            <td>${fmtDate(j.start_date)} — ${fmtDate(j.end_date)}</td>
          </tr>
        `).join('')}</tbody>
      </table></div>
    </div>
  `;

  $('#add-job').onclick = () => showJobForm();
}

async function showJobForm() {
  const customers = await api('customers');
  showModal('New Job', `
    <form id="job-form" class="form-grid">
      <div class="form-group"><label>Customer *</label>
        <select name="customer_id" required>${customers.map(c => `<option value="${c.id}">${c.name}</option>`).join('')}</select>
      </div>
      <div class="form-group"><label>Job Name *</label><input name="name" required></div>
      <div class="form-group full"><label>Site Address</label><input name="site_address"></div>
      <div class="form-group"><label>Start Date</label><input name="start_date" type="date"></div>
      <div class="form-group"><label>End Date</label><input name="end_date" type="date"></div>
      <div class="form-group"><label>Estimated Value</label><input name="estimated_value" type="number" step="0.01" value="0"></div>
      <div class="form-group full"><label>Notes</label><textarea name="notes"></textarea></div>
    </form>
  `, `<button class="btn btn-secondary" onclick="document.getElementById('modal-overlay').classList.add('hidden')">Cancel</button>
      <button class="btn btn-primary" id="save-job">Create Job</button>`);

  $('#save-job').onclick = async () => {
    const body = Object.fromEntries(new FormData($('#job-form')));
    body.customer_id = parseInt(body.customer_id);
    body.estimated_value = parseFloat(body.estimated_value);
    try {
      await api('jobs', { method: 'POST', body });
      hideModal(); toast('Job created'); renderJobs();
    } catch (e) { toast(e.message); }
  };
}

// --- Quotes ---

async function renderQuotes() {
  topbarActions().innerHTML = '<button class="btn btn-primary" id="add-quote">+ New Quote</button>';
  content().innerHTML = '<div class="text-muted">Loading...</div>';
  const data = await api('quotes');

  content().innerHTML = `
    <div class="card">
      <div class="table-wrap"><table>
        <thead><tr>
          <th>Quote #</th><th>Customer</th><th>Job</th><th>Date</th><th>Valid Until</th><th>Total</th><th>Status</th><th>Actions</th>
        </tr></thead>
        <tbody>${data.map(q => `
          <tr>
            <td><strong>${q.quote_number}</strong></td>
            <td>${q.customer_name}</td>
            <td>${q.job_name || '—'}</td>
            <td>${fmtDate(q.quote_date)}</td>
            <td>${fmtDate(q.valid_until)}</td>
            <td>${fmt(q.total)}</td>
            <td>${badge(q.status)}</td>
            <td class="gap-8">
              <button class="btn btn-sm btn-secondary view-quote" data-id="${q.id}">View</button>
              ${q.status === 'sent' ? `<button class="btn btn-sm btn-primary accept-quote" data-id="${q.id}">Accept</button>` : ''}
            </td>
          </tr>
        `).join('')}</tbody>
      </table></div>
    </div>
  `;

  $('#add-quote').onclick = () => showQuoteForm();
  document.querySelectorAll('.view-quote').forEach(btn => {
    btn.onclick = () => viewQuote(data.find(q => q.id == btn.dataset.id));
  });
  document.querySelectorAll('.accept-quote').forEach(btn => {
    btn.onclick = async () => {
      await api(`quotes/${btn.dataset.id}/status`, { method: 'PATCH', body: { status: 'accepted' } });
      toast('Quote accepted'); renderQuotes();
    };
  });
}

function viewQuote(q) {
  showModal(q.quote_number, `
    <dl class="detail-grid">
      <dt>Customer</dt><dd>${q.customer_name}</dd>
      <dt>Job</dt><dd>${q.job_name || '—'}</dd>
      <dt>Status</dt><dd>${badge(q.status)}</dd>
      <dt>Total</dt><dd class="text-accent">${fmt(q.total)}</dd>
    </dl>
    <div class="mt-16 table-wrap"><table>
      <thead><tr><th>Description</th><th>Qty</th><th>Price</th><th>Total</th></tr></thead>
      <tbody>${q.lines.map(l => `<tr><td>${l.description}</td><td>${l.quantity}</td><td>${fmt(l.unit_price)}</td><td>${fmt(l.line_total)}</td></tr>`).join('')}</tbody>
    </table></div>
  `, '<button class="btn btn-secondary" onclick="document.getElementById(\'modal-overlay\').classList.add(\'hidden\')">Close</button>');
}

async function showQuoteForm() {
  const [customers, jobs, products] = await Promise.all([api('customers'), api('jobs'), api('products')]);
  showModal('New Quote', `
    <form id="quote-form">
      <div class="form-grid">
        <div class="form-group"><label>Customer *</label>
          <select name="customer_id" required>${customers.map(c => `<option value="${c.id}">${c.name}</option>`).join('')}</select>
        </div>
        <div class="form-group"><label>Job</label>
          <select name="job_id"><option value="">— None —</option>${jobs.filter(j => j.status === 'active').map(j => `<option value="${j.id}">${j.job_number} — ${j.name}</option>`).join('')}</select>
        </div>
      </div>
      <div class="line-items mt-16">
        <div class="line-items-header"><span>Description</span><span>Qty</span><span>Price</span><span>Total</span><span></span></div>
        <div id="quote-lines"></div>
        <button type="button" class="btn btn-sm btn-secondary mt-16" id="add-quote-line">+ Add Line</button>
      </div>
    </form>
  `, `<button class="btn btn-secondary" onclick="document.getElementById('modal-overlay').classList.add('hidden')">Cancel</button>
      <button class="btn btn-primary" id="save-quote">Create Quote</button>`);

  const linesEl = $('#quote-lines');
  function addLine() {
    const row = document.createElement('div');
    row.className = 'line-item-row';
    row.innerHTML = `
      <select class="line-product"><option value="">Custom line</option>
        ${products.map(p => `<option value="${p.id}" data-price="${p.price}" data-name="${p.name}">${p.sku} — ${p.name}</option>`).join('')}
      </select>
      <input type="number" class="line-qty" value="1" min="0.01" step="0.01">
      <input type="number" class="line-price" step="0.01" value="0">
      <span class="line-total">$0.00</span>
      <button type="button" class="btn-icon remove-line">&times;</button>
    `;
    const descInput = document.createElement('input');
    descInput.className = 'line-desc';
    descInput.placeholder = 'Description';
    descInput.style.display = 'none';
    row.querySelector('.line-product').before(descInput);

    const update = () => {
      const qty = parseFloat(row.querySelector('.line-qty').value) || 0;
      const price = parseFloat(row.querySelector('.line-price').value) || 0;
      row.querySelector('.line-total').textContent = fmt(qty * price);
    };
    row.querySelector('.line-product').onchange = (e) => {
      const opt = e.target.selectedOptions[0];
      if (opt.value) {
        row.querySelector('.line-price').value = opt.dataset.price;
        descInput.style.display = 'none';
      } else {
        descInput.style.display = 'block';
      }
      update();
    };
    row.querySelector('.line-qty').oninput = update;
    row.querySelector('.line-price').oninput = update;
    row.querySelector('.remove-line').onclick = () => row.remove();
    linesEl.appendChild(row);
  }
  addLine();
  $('#add-quote-line').onclick = addLine;

  $('#save-quote').onclick = async () => {
    const fd = Object.fromEntries(new FormData($('#quote-form')));
    const lines = [...linesEl.querySelectorAll('.line-item-row')].map(row => {
      const sel = row.querySelector('.line-product');
      const pid = sel.value ? parseInt(sel.value) : null;
      const desc = pid ? sel.selectedOptions[0].dataset.name : row.querySelector('.line-desc').value;
      return { product_id: pid, description: desc, quantity: parseFloat(row.querySelector('.line-qty').value), unit_price: parseFloat(row.querySelector('.line-price').value) };
    }).filter(l => l.description);
    try {
      await api('quotes', { method: 'POST', body: { customer_id: parseInt(fd.customer_id), job_id: fd.job_id ? parseInt(fd.job_id) : null, lines } });
      hideModal(); toast('Quote created'); renderQuotes();
    } catch (e) { toast(e.message); }
  };
}

// --- Sales Orders ---

async function renderSalesOrders() {
  topbarActions().innerHTML = '<button class="btn btn-primary" id="add-so">+ New Sales Order</button>';
  content().innerHTML = '<div class="text-muted">Loading...</div>';
  const data = await api('sales-orders');

  content().innerHTML = `
    <div class="card">
      <div class="table-wrap"><table>
        <thead><tr>
          <th>Order #</th><th>Customer</th><th>Job</th><th>Date</th><th>Required</th><th>Total</th><th>Status</th><th>Actions</th>
        </tr></thead>
        <tbody>${data.map(so => `
          <tr>
            <td><strong>${so.order_number}</strong></td>
            <td>${so.customer_name}</td>
            <td>${so.job_name || '—'}</td>
            <td>${fmtDate(so.order_date)}</td>
            <td>${fmtDate(so.required_date)}</td>
            <td>${fmt(so.total)}</td>
            <td>${badge(so.status)}</td>
            <td class="gap-8">
              <button class="btn btn-sm btn-secondary view-so" data-id="${so.id}">View</button>
              ${['confirmed','partial'].includes(so.status) ? `<button class="btn btn-sm btn-primary ship-so" data-id="${so.id}">Ship</button>` : ''}
              ${!['cancelled','delivered'].includes(so.status) ? `<button class="btn btn-sm btn-secondary invoice-so" data-id="${so.id}">Invoice</button>` : ''}
            </td>
          </tr>
        `).join('')}</tbody>
      </table></div>
    </div>
  `;

  $('#add-so').onclick = () => showSOForm();
  document.querySelectorAll('.view-so').forEach(btn => {
    btn.onclick = () => viewSO(data.find(s => s.id == btn.dataset.id));
  });
  document.querySelectorAll('.ship-so').forEach(btn => {
    btn.onclick = () => shipSO(data.find(s => s.id == btn.dataset.id));
  });
  document.querySelectorAll('.invoice-so').forEach(btn => {
    btn.onclick = async () => {
      try {
        await api(`invoices/from-order/${btn.dataset.id}`, { method: 'POST' });
        toast('Invoice created from order'); renderInvoices(); navigate('invoices');
      } catch (e) { toast(e.message); }
    };
  });
}

function viewSO(so) {
  showModal(so.order_number, `
    <dl class="detail-grid">
      <dt>Customer</dt><dd>${so.customer_name}</dd>
      <dt>Job</dt><dd>${so.job_name || '—'}</dd>
      <dt>Status</dt><dd>${badge(so.status)}</dd>
      <dt>Total</dt><dd class="text-accent">${fmt(so.total)}</dd>
    </dl>
    <div class="mt-16 table-wrap"><table>
      <thead><tr><th>Product</th><th>Ordered</th><th>Shipped</th><th>Price</th><th>Total</th></tr></thead>
      <tbody>${so.lines.map(l => `<tr><td>${l.product_name}</td><td>${l.quantity_ordered}</td><td>${l.quantity_shipped}</td><td>${fmt(l.unit_price)}</td><td>${fmt(l.line_total)}</td></tr>`).join('')}</tbody>
    </table></div>
  `, '<button class="btn btn-secondary" onclick="document.getElementById(\'modal-overlay\').classList.add(\'hidden\')">Close</button>');
}

async function shipSO(so) {
  showModal(`Ship ${so.order_number}`, `
    <div class="table-wrap"><table>
      <thead><tr><th>Product</th><th>Ordered</th><th>Shipped</th><th>Ship Qty</th></tr></thead>
      <tbody>${so.lines.map(l => `
        <tr data-line-id="${l.id}">
          <td>${l.product_name}</td><td>${l.quantity_ordered}</td><td>${l.quantity_shipped}</td>
          <td><input type="number" class="ship-qty" min="0" max="${l.quantity_ordered - l.quantity_shipped}"
            value="${l.quantity_ordered - l.quantity_shipped}" style="width:80px"></td>
        </tr>
      `).join('')}</tbody>
    </table></div>
  `, `<button class="btn btn-secondary" onclick="document.getElementById('modal-overlay').classList.add('hidden')">Cancel</button>
      <button class="btn btn-primary" id="confirm-ship">Confirm Shipment</button>`);

  $('#confirm-ship').onclick = async () => {
    const lines = [...document.querySelectorAll('tr[data-line-id]')].map(tr => ({
      line_id: parseInt(tr.dataset.lineId),
      quantity: parseInt(tr.querySelector('.ship-qty').value) || 0,
    })).filter(l => l.quantity > 0);
    try {
      await api(`sales-orders/${so.id}/ship`, { method: 'POST', body: { lines } });
      hideModal(); toast('Shipment processed'); renderSalesOrders();
    } catch (e) { toast(e.message); }
  };
}

async function showSOForm() {
  const [customers, jobs, products] = await Promise.all([api('customers'), api('jobs'), api('products')]);
  showModal('New Sales Order', `
    <form id="so-form">
      <div class="form-grid">
        <div class="form-group"><label>Customer *</label>
          <select name="customer_id" required>${customers.map(c => `<option value="${c.id}">${c.name}</option>`).join('')}</select>
        </div>
        <div class="form-group"><label>Job</label>
          <select name="job_id"><option value="">— None —</option>${jobs.filter(j => j.status === 'active').map(j => `<option value="${j.id}">${j.job_number}</option>`).join('')}</select>
        </div>
        <div class="form-group"><label>Required Date</label><input name="required_date" type="date"></div>
      </div>
      <div class="line-items mt-16">
        <div class="line-items-header"><span>Product</span><span>Qty</span><span>Price</span><span>Total</span><span></span></div>
        <div id="so-lines"></div>
        <button type="button" class="btn btn-sm btn-secondary mt-16" id="add-so-line">+ Add Line</button>
      </div>
    </form>
  `, `<button class="btn btn-secondary" onclick="document.getElementById('modal-overlay').classList.add('hidden')">Cancel</button>
      <button class="btn btn-primary" id="save-so">Create Order</button>`);

  const linesEl = $('#so-lines');
  const productOpts = products.map(p => `<option value="${p.id}" data-price="${p.price}">${p.sku} — ${p.name} (stock: ${p.quantity_on_hand})</option>`).join('');

  function addLine() {
    const row = document.createElement('div');
    row.className = 'line-item-row';
    row.innerHTML = `
      <select class="line-product">${productOpts}</select>
      <input type="number" class="line-qty" value="1" min="1">
      <input type="number" class="line-price" step="0.01" value="${products[0]?.price || 0}">
      <span class="line-total">${fmt(products[0]?.price || 0)}</span>
      <button type="button" class="btn-icon remove-line">&times;</button>
    `;
    const update = () => {
      const qty = parseFloat(row.querySelector('.line-qty').value) || 0;
      const price = parseFloat(row.querySelector('.line-price').value) || 0;
      row.querySelector('.line-total').textContent = fmt(qty * price);
    };
    row.querySelector('.line-product').onchange = (e) => {
      row.querySelector('.line-price').value = e.target.selectedOptions[0].dataset.price;
      update();
    };
    row.querySelector('.line-qty').oninput = update;
    row.querySelector('.line-price').oninput = update;
    row.querySelector('.remove-line').onclick = () => row.remove();
    linesEl.appendChild(row);
  }
  addLine();
  $('#add-so-line').onclick = addLine;

  $('#save-so').onclick = async () => {
    const fd = Object.fromEntries(new FormData($('#so-form')));
    const lines = [...linesEl.querySelectorAll('.line-item-row')].map(row => ({
      product_id: parseInt(row.querySelector('.line-product').value),
      quantity_ordered: parseInt(row.querySelector('.line-qty').value),
      unit_price: parseFloat(row.querySelector('.line-price').value),
    }));
    try {
      await api('sales-orders', { method: 'POST', body: {
        customer_id: parseInt(fd.customer_id),
        job_id: fd.job_id ? parseInt(fd.job_id) : null,
        required_date: fd.required_date,
        status: 'confirmed',
        lines,
      }});
      hideModal(); toast('Sales order created'); renderSalesOrders();
    } catch (e) { toast(e.message); }
  };
}

// --- Invoices ---

async function renderInvoices() {
  topbarActions().innerHTML = '<button class="btn btn-primary" id="add-invoice">+ New Invoice</button>';
  content().innerHTML = '<div class="text-muted">Loading...</div>';
  const data = await api('invoices');

  content().innerHTML = `
    <div class="card">
      <div class="table-wrap"><table>
        <thead><tr>
          <th>Invoice #</th><th>Customer</th><th>Job</th><th>Date</th><th>Due</th><th>Total</th><th>Paid</th><th>Balance</th><th>Status</th><th>Actions</th>
        </tr></thead>
        <tbody>${data.map(inv => `
          <tr>
            <td><strong>${inv.invoice_number}</strong></td>
            <td>${inv.customer_name}</td>
            <td>${inv.job_name || '—'}</td>
            <td>${fmtDate(inv.invoice_date)}</td>
            <td>${fmtDate(inv.due_date)}</td>
            <td>${fmt(inv.total)}</td>
            <td>${fmt(inv.amount_paid)}</td>
            <td class="${inv.total - inv.amount_paid > 0 ? 'text-accent' : 'text-success'}">${fmt(inv.total - inv.amount_paid)}</td>
            <td>${badge(inv.status)}</td>
            <td class="gap-8">
              <button class="btn btn-sm btn-secondary view-inv" data-id="${inv.id}">View</button>
              ${inv.status !== 'paid' && inv.status !== 'void' ? `<button class="btn btn-sm btn-primary pay-inv" data-id="${inv.id}" data-balance="${inv.total - inv.amount_paid}">Payment</button>` : ''}
              ${inv.status === 'draft' ? `<button class="btn btn-sm btn-secondary send-inv" data-id="${inv.id}">Send</button>` : ''}
            </td>
          </tr>
        `).join('')}</tbody>
      </table></div>
    </div>
  `;

  $('#add-invoice').onclick = () => showInvoiceForm();
  document.querySelectorAll('.view-inv').forEach(btn => {
    btn.onclick = () => viewInvoice(data.find(i => i.id == btn.dataset.id));
  });
  document.querySelectorAll('.pay-inv').forEach(btn => {
    btn.onclick = () => showPaymentForm(data.find(i => i.id == btn.dataset.id));
  });
  document.querySelectorAll('.send-inv').forEach(btn => {
    btn.onclick = async () => {
      await api(`invoices/${btn.dataset.id}/status`, { method: 'PATCH', body: { status: 'sent' } });
      toast('Invoice sent'); renderInvoices();
    };
  });
}

function viewInvoice(inv) {
  showModal(inv.invoice_number, `
    <dl class="detail-grid">
      <dt>Customer</dt><dd>${inv.customer_name}</dd>
      <dt>Status</dt><dd>${badge(inv.status)}</dd>
      <dt>Total</dt><dd class="text-accent">${fmt(inv.total)}</dd>
      <dt>Balance Due</dt><dd>${fmt(inv.total - inv.amount_paid)}</dd>
    </dl>
    <div class="mt-16 table-wrap"><table>
      <thead><tr><th>Description</th><th>Qty</th><th>Price</th><th>Total</th></tr></thead>
      <tbody>${inv.lines.map(l => `<tr><td>${l.description}</td><td>${l.quantity}</td><td>${fmt(l.unit_price)}</td><td>${fmt(l.line_total)}</td></tr>`).join('')}</tbody>
    </table></div>
  `, '<button class="btn btn-secondary" onclick="document.getElementById(\'modal-overlay\').classList.add(\'hidden\')">Close</button>');
}

function showPaymentForm(inv) {
  const balance = inv.total - inv.amount_paid;
  showModal(`Payment — ${inv.invoice_number}`, `
    <form id="payment-form" class="form-grid">
      <div class="form-group"><label>Balance Due</label><input readonly value="${fmt(balance)}"></div>
      <div class="form-group"><label>Payment Amount *</label><input name="amount" type="number" step="0.01" required value="${balance.toFixed(2)}"></div>
    </form>
  `, `<button class="btn btn-secondary" onclick="document.getElementById('modal-overlay').classList.add('hidden')">Cancel</button>
      <button class="btn btn-primary" id="save-payment">Record Payment</button>`);

  $('#save-payment').onclick = async () => {
    const amount = parseFloat(new FormData($('#payment-form')).get('amount'));
    try {
      await api(`invoices/${inv.id}/payment`, { method: 'POST', body: { amount } });
      hideModal(); toast('Payment recorded'); renderInvoices();
    } catch (e) { toast(e.message); }
  };
}

async function showInvoiceForm() {
  const [customers, jobs, products] = await Promise.all([api('customers'), api('jobs'), api('products')]);
  showModal('New Invoice', `
    <form id="inv-form">
      <div class="form-grid">
        <div class="form-group"><label>Customer *</label>
          <select name="customer_id" required>${customers.map(c => `<option value="${c.id}">${c.name}</option>`).join('')}</select>
        </div>
        <div class="form-group"><label>Job</label>
          <select name="job_id"><option value="">— None —</option>${jobs.map(j => `<option value="${j.id}">${j.job_number}</option>`).join('')}</select>
        </div>
      </div>
      <div class="line-items mt-16">
        <div class="line-items-header"><span>Description</span><span>Qty</span><span>Price</span><span>Total</span><span></span></div>
        <div id="inv-lines"></div>
        <button type="button" class="btn btn-sm btn-secondary mt-16" id="add-inv-line">+ Add Line</button>
      </div>
    </form>
  `, `<button class="btn btn-secondary" onclick="document.getElementById('modal-overlay').classList.add('hidden')">Cancel</button>
      <button class="btn btn-primary" id="save-inv">Create Invoice</button>`);

  const linesEl = $('#inv-lines');
  function addLine() {
    const row = document.createElement('div');
    row.className = 'line-item-row';
    row.innerHTML = `
      <select class="line-product"><option value="">Custom</option>
        ${products.map(p => `<option value="${p.id}" data-price="${p.price}" data-name="${p.name}">${p.sku} — ${p.name}</option>`).join('')}
      </select>
      <input type="number" class="line-qty" value="1" min="0.01" step="0.01">
      <input type="number" class="line-price" step="0.01" value="0">
      <span class="line-total">$0.00</span>
      <button type="button" class="btn-icon remove-line">&times;</button>
    `;
    const descInput = document.createElement('input');
    descInput.className = 'line-desc'; descInput.placeholder = 'Description'; descInput.style.display = 'none';
    row.querySelector('.line-product').before(descInput);
    const update = () => {
      row.querySelector('.line-total').textContent = fmt((parseFloat(row.querySelector('.line-qty').value)||0) * (parseFloat(row.querySelector('.line-price').value)||0));
    };
    row.querySelector('.line-product').onchange = (e) => {
      const opt = e.target.selectedOptions[0];
      if (opt.value) { row.querySelector('.line-price').value = opt.dataset.price; descInput.style.display = 'none'; }
      else descInput.style.display = 'block';
      update();
    };
    row.querySelector('.line-qty').oninput = update;
    row.querySelector('.line-price').oninput = update;
    row.querySelector('.remove-line').onclick = () => row.remove();
    linesEl.appendChild(row);
  }
  addLine();
  $('#add-inv-line').onclick = addLine;

  $('#save-inv').onclick = async () => {
    const fd = Object.fromEntries(new FormData($('#inv-form')));
    const lines = [...linesEl.querySelectorAll('.line-item-row')].map(row => {
      const sel = row.querySelector('.line-product');
      const pid = sel.value ? parseInt(sel.value) : null;
      return { product_id: pid, description: pid ? sel.selectedOptions[0].dataset.name : row.querySelector('.line-desc').value,
        quantity: parseFloat(row.querySelector('.line-qty').value), unit_price: parseFloat(row.querySelector('.line-price').value) };
    }).filter(l => l.description);
    try {
      await api('invoices', { method: 'POST', body: { customer_id: parseInt(fd.customer_id), job_id: fd.job_id ? parseInt(fd.job_id) : null, lines } });
      hideModal(); toast('Invoice created'); renderInvoices();
    } catch (e) { toast(e.message); }
  };
}

// --- Reports ---

async function renderReports() {
  await renderReportsPage({ topbarActions, content, api, fmt, fmtDate, badge, $ });
}

async function renderReminders() {
  await renderRemindersPage({ topbarActions, content, api, fmt, fmtDate, badge, $, toast, showModal, hideModal });
}

// Init
renderNav();
navigate('dashboard');
