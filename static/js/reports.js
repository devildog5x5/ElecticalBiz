/** Full reporting package UI */

let reportData = null;
let reportSection = 'financial';
let reportDateFrom = '';
let reportDateTo = '';

function exportCsv(type) {
  const params = new URLSearchParams({ type });
  if (reportDateFrom) params.set('from', reportDateFrom);
  if (reportDateTo) params.set('to', reportDateTo);
  window.open(`/api/reports/export?${params}`, '_blank');
}

function reportTable(title, headers, rows, renderRow, exportType) {
  return `
    <div class="card report-panel">
      <div class="card-header">
        <div class="card-title">${title}</div>
        ${exportType ? `<button class="btn btn-sm btn-secondary export-btn" data-export="${exportType}">⬇ CSV</button>` : ''}
      </div>
      <div class="table-wrap"><table>
        <thead><tr>${headers.map(h => `<th>${h}</th>`).join('')}</tr></thead>
        <tbody>${rows.length ? rows.map(renderRow).join('') : `<tr><td colspan="${headers.length}" class="text-muted">No data for selected period</td></tr>`}</tbody>
      </table></div>
    </div>`;
}

function barChart(items, valueKey, labelKey, maxBars = 8) {
  const top = items.slice(0, maxBars);
  const max = Math.max(...top.map(i => i[valueKey] || 0), 1);
  const moneyKeys = ['total', 'revenue', 'spend', 'value', 'balance', 'collected', 'invoiced', 'purchases', 'sales'];
  return `<div class="bar-chart">${top.map(item => {
    const val = item[valueKey] || 0;
    const pct = Math.round((val / max) * 100);
    const display = typeof val === 'number' && moneyKeys.some(k => valueKey.includes(k)) ? fmt(val) : val;
    return `<div class="bar-row">
      <div class="bar-label">${item[labelKey]}</div>
      <div class="bar-track"><div class="bar-fill" style="width:${pct}%"></div></div>
      <div class="bar-value">${display}</div>
    </div>`;
  }).join('')}</div>`;
}

function renderFinancialReports(f) {
  return `
    <div class="metric-grid mb-20">
      <div class="metric-card"><div class="metric-label">Total Revenue</div><div class="metric-value gold">${fmt(f.revenue)}</div></div>
      <div class="metric-card"><div class="metric-label">Collected</div><div class="metric-value green">${fmt(f.collected)}</div></div>
      <div class="metric-card"><div class="metric-label">Outstanding A/R</div><div class="metric-value red">${fmt(f.outstanding_ar)}</div></div>
      <div class="metric-card"><div class="metric-label">COGS (Received POs)</div><div class="metric-value blue">${fmt(f.cogs)}</div></div>
      <div class="metric-card"><div class="metric-label">Gross Profit</div><div class="metric-value green">${fmt(f.gross_profit)}</div></div>
      <div class="metric-card"><div class="metric-label">Gross Margin</div><div class="metric-value purple">${f.gross_margin_pct}%</div></div>
      <div class="metric-card"><div class="metric-label">Inventory (Cost)</div><div class="metric-value blue">${fmt(f.inventory_cost)}</div></div>
      <div class="metric-card"><div class="metric-label">Open A/P (POs)</div><div class="metric-value amber">${fmt(f.open_ap)}</div></div>
    </div>

    <div class="grid grid-2 mb-20">
      ${reportTable('Profit & Loss Summary', ['Metric', 'Amount'], [
        { metric: 'Revenue', amount: f.revenue },
        { metric: 'Cost of Goods Sold', amount: f.cogs },
        { metric: 'Gross Profit', amount: f.gross_profit },
        { metric: 'Gross Margin', amount: `${f.gross_margin_pct}%` },
        { metric: 'Inventory at Cost', amount: f.inventory_cost },
        { metric: 'Inventory at Retail', amount: f.inventory_retail },
      ], r => `<tr><td>${r.metric}</td><td><strong>${typeof r.amount === 'number' ? fmt(r.amount) : r.amount}</strong></td></tr>`)}

      ${reportTable('A/R Aging Summary', ['Bucket', 'Invoices', 'Balance'], f.ar_aging,
        r => `<tr><td>${r.bucket}</td><td>${r.invoice_count}</td><td class="text-accent">${fmt(r.balance)}</td></tr>`)}
    </div>

    ${reportTable('A/R Detail — Open Invoices', ['Invoice', 'Customer', 'Due', 'Balance', 'Days Overdue', 'Status'],
      f.ar_detail, r => `<tr>
        <td><strong>${r.invoice_number}</strong></td><td>${r.customer_name}</td>
        <td>${fmtDate(r.due_date)}</td><td class="text-accent">${fmt(r.balance)}</td>
        <td class="${r.days_overdue > 0 ? 'low-stock' : ''}">${r.days_overdue > 0 ? r.days_overdue : '—'}</td>
        <td>${badge(r.status)}</td></tr>`, 'ar_aging')}

    <div class="grid grid-2 mt-16">
      ${reportTable('Open A/P by Supplier', ['Supplier', 'Type', 'Open POs', 'Value'], f.ap_summary,
        r => `<tr><td>${r.supplier_name}</td><td>${badge(r.type)}</td><td>${r.open_pos}</td><td>${fmt(r.open_value)}</td></tr>`, 'ap_summary')}

      ${reportTable('Monthly Revenue Trend', ['Month', 'Invoices', 'Revenue', 'Collected'], f.monthly_revenue,
        r => `<tr><td>${r.month}</td><td>${r.invoices}</td><td>${fmt(r.revenue)}</td><td class="text-success">${fmt(r.collected)}</td></tr>`, 'monthly_revenue')}
    </div>
  `;
}

function renderSalesReports(s) {
  return `
    <div class="metric-grid mb-20" style="grid-template-columns: repeat(3, 1fr);">
      <div class="metric-card"><div class="metric-label">Quote Conversion Rate</div><div class="metric-value green">${s.quote_conversion_rate}%</div></div>
      <div class="metric-card"><div class="metric-label">Total Quotes</div><div class="metric-value blue">${s.quote_total}</div></div>
      <div class="metric-card"><div class="metric-label">Quote Pipeline Value</div><div class="metric-value gold">${fmt(s.quote_pipeline.reduce((a, q) => a + q.value, 0))}</div></div>
    </div>

    <div class="grid grid-2 mb-20">
      <div class="card report-panel">
        <div class="card-header"><div class="card-title">Revenue by Category</div></div>
        ${barChart(s.by_category, 'revenue', 'category')}
      </div>
      <div class="card report-panel">
        <div class="card-header"><div class="card-title">Quote Pipeline</div></div>
        ${s.quote_pipeline.length ? s.quote_pipeline.map(q => `
          <div class="pipeline-row"><span>${badge(q.status)}</span><span>${q.count} quotes</span><span class="text-accent">${fmt(q.value)}</span></div>
        `).join('') : '<p class="text-muted">No quotes in period</p>'}
      </div>
    </div>

    ${reportTable('Sales by Customer', ['Customer', 'Type', 'Invoices', 'Sales', 'Collected', 'Outstanding'],
      s.by_customer, r => `<tr><td><strong>${r.name}</strong></td><td>${badge(r.type)}</td><td>${r.invoice_count}</td>
      <td>${fmt(r.total_sales)}</td><td class="text-success">${fmt(r.collected)}</td><td class="text-accent">${fmt(r.outstanding)}</td></tr>`, 'sales_by_customer')}

    <div class="grid grid-2 mt-16">
      ${reportTable('Top Products by Revenue', ['SKU', 'Product', 'Category', 'Qty', 'Revenue'], s.top_products,
        r => `<tr><td><code>${r.sku}</code></td><td>${r.name}</td><td>${r.category}</td><td>${r.qty_sold}</td><td>${fmt(r.revenue)}</td></tr>`, 'top_products')}

      ${reportTable('Sales by Category', ['Category', 'Units', 'Revenue'], s.by_category,
        r => `<tr><td>${r.category}</td><td>${r.units_sold}</td><td>${fmt(r.revenue)}</td></tr>`, 'sales_by_category')}
    </div>

    ${reportTable('Sales by Job', ['Job #', 'Job', 'Customer', 'Status', 'Estimated', 'Invoiced', 'Collected'],
      s.by_job, r => `<tr><td><strong>${r.job_number}</strong></td><td>${r.job_name}</td><td>${r.customer_name}</td>
      <td>${badge(r.status)}</td><td>${fmt(r.estimated_value)}</td><td>${fmt(r.invoiced)}</td><td class="text-success">${fmt(r.collected)}</td></tr>`, 'sales_by_job')}
  `;
}

function renderPurchasingReports(p) {
  const totalSpend = p.by_supplier.reduce((a, s) => a + s.total_purchases, 0);
  return `
    <div class="metric-grid mb-20" style="grid-template-columns: repeat(3, 1fr);">
      <div class="metric-card"><div class="metric-label">Total Purchases</div><div class="metric-value gold">${fmt(totalSpend)}</div></div>
      <div class="metric-card"><div class="metric-label">Active Suppliers</div><div class="metric-value blue">${p.by_supplier.filter(s => s.po_count > 0).length}</div></div>
      <div class="metric-card"><div class="metric-label">PO Status Types</div><div class="metric-value purple">${p.po_status.length}</div></div>
    </div>

    <div class="grid grid-2 mb-20">
      <div class="card report-panel">
        <div class="card-header"><div class="card-title">Spend by Supplier</div>
          <button class="btn btn-sm btn-secondary export-btn" data-export="purchases_by_supplier">⬇ CSV</button></div>
        ${barChart(p.by_supplier.filter(s => s.total_purchases > 0), 'total_purchases', 'name')}
      </div>
      <div class="card report-panel">
        <div class="card-header"><div class="card-title">PO Status Breakdown</div></div>
        ${p.po_status.map(s => `<div class="pipeline-row"><span>${badge(s.status)}</span><span>${s.count} orders</span><span class="text-accent">${fmt(s.value)}</span></div>`).join('') || '<p class="text-muted">No POs in period</p>'}
      </div>
    </div>

    ${reportTable('Purchases by Supplier', ['Supplier', 'Type', 'PO Count', 'Total Spend'], p.by_supplier,
      r => `<tr><td><strong>${r.name}</strong></td><td>${badge(r.type)}</td><td>${r.po_count}</td><td>${fmt(r.total_purchases)}</td></tr>`, 'purchases_by_supplier')}

    ${reportTable('Purchases by Category', ['Category', 'Units Ordered', 'Spend'], p.by_category,
      r => `<tr><td>${r.category}</td><td>${r.units}</td><td>${fmt(r.spend)}</td></tr>`, 'purchases_by_category')}
  `;
}

function renderInventoryReports(inv) {
  const totalCost = inv.by_category.reduce((a, c) => a + c.cost_value, 0);
  const totalRetail = inv.by_category.reduce((a, c) => a + c.retail_value, 0);
  return `
    <div class="metric-grid mb-20">
      <div class="metric-card"><div class="metric-label">Inventory at Cost</div><div class="metric-value gold">${fmt(totalCost)}</div></div>
      <div class="metric-card"><div class="metric-label">Inventory at Retail</div><div class="metric-value green">${fmt(totalRetail)}</div></div>
      <div class="metric-card"><div class="metric-label">Markup Potential</div><div class="metric-value purple">${fmt(totalRetail - totalCost)}</div></div>
      <div class="metric-card"><div class="metric-label">Low Stock SKUs</div><div class="metric-value red">${inv.low_stock.length}</div></div>
    </div>

    ${reportTable('Inventory Valuation by Category', ['Category', 'Products', 'Units', 'Cost Value', 'Retail Value'],
      inv.by_category, r => `<tr><td>${r.category}</td><td>${r.product_count}</td><td>${r.total_units}</td>
      <td>${fmt(r.cost_value)}</td><td class="text-success">${fmt(r.retail_value)}</td></tr>`, 'inventory_valuation')}

    <div class="grid grid-2 mt-16">
      ${reportTable('Low Stock / Reorder Report', ['SKU', 'Product', 'On Hand', 'Reorder', 'Need', 'Supplier', 'Cost'],
        inv.low_stock, r => `<tr><td><code>${r.sku}</code></td><td>${r.name}</td>
        <td class="low-stock">${r.quantity_on_hand}</td><td>${r.reorder_level}</td><td>${r.qty_needed}</td>
        <td>${r.supplier_name || '—'}</td><td>${fmt(r.cost)}</td></tr>`, 'low_stock')}

      ${reportTable('Product Margin Analysis', ['SKU', 'Product', 'Cost', 'Price', 'Margin %', 'On Hand', 'Potential Profit'],
        inv.margins, r => `<tr><td><code>${r.sku}</code></td><td>${r.name}</td><td>${fmt(r.cost)}</td><td>${fmt(r.price)}</td>
        <td class="text-success">${r.margin_pct}%</td><td>${r.quantity_on_hand}</td><td>${fmt(r.potential_profit)}</td></tr>`, 'product_margins')}
    </div>
  `;
}

function renderOperationsReports(op) {
  const activeJobs = op.job_summary.find(j => j.status === 'active');
  return `
    <div class="metric-grid mb-20" style="grid-template-columns: repeat(3, 1fr);">
      <div class="metric-card"><div class="metric-label">Open Orders to Fulfill</div><div class="metric-value blue">${op.fulfillment.length}</div></div>
      <div class="metric-card"><div class="metric-label">Active Jobs</div><div class="metric-value green">${activeJobs?.count || 0}</div></div>
      <div class="metric-card"><div class="metric-label">Active Pipeline Value</div><div class="metric-value gold">${fmt(activeJobs?.pipeline_value || 0)}</div></div>
    </div>

    <div class="grid grid-2 mb-20">
      <div class="card report-panel">
        <div class="card-header"><div class="card-title">Job Status Summary</div></div>
        ${op.job_summary.map(j => `<div class="pipeline-row"><span>${badge(j.status)}</span><span>${j.count} jobs</span><span class="text-accent">${fmt(j.pipeline_value)}</span></div>`).join('')}
      </div>
    </div>

    ${reportTable('Order Fulfillment — Open Sales Orders', ['Order #', 'Customer', 'Status', 'Required', 'Total', 'Ordered', 'Shipped'],
      op.fulfillment, r => `<tr><td><strong>${r.order_number}</strong></td><td>${r.customer_name}</td><td>${badge(r.status)}</td>
      <td>${fmtDate(r.required_date)}</td><td>${fmt(r.total)}</td><td>${r.qty_ordered}</td><td>${r.qty_shipped}</td></tr>`, 'order_fulfillment')}
  `;
}

function renderReportSection() {
  if (!reportData) return;
  const sections = {
    financial: renderFinancialReports(reportData.financial),
    sales: renderSalesReports(reportData.sales),
    purchasing: renderPurchasingReports(reportData.purchasing),
    inventory: renderInventoryReports(reportData.inventory),
    operations: renderOperationsReports(reportData.operations),
  };
  $('#report-body').innerHTML = sections[reportSection] || '';
  document.querySelectorAll('.export-btn').forEach(btn => {
    btn.onclick = () => exportCsv(btn.dataset.export);
  });
}

export async function renderReports(deps) {
  const { topbarActions, content, api, fmt, fmtDate, badge, $ } = deps;
  Object.assign(window, { fmt, fmtDate, badge, $ });

  topbarActions().innerHTML = `
    <button class="btn btn-secondary" id="print-reports">🖨 Print</button>
    <button class="btn btn-primary" id="refresh-reports">↻ Refresh</button>
  `;

  content().innerHTML = `
    <div class="report-toolbar">
      <div class="report-filters">
        <label>From <input type="date" id="report-from" value="${reportDateFrom}"></label>
        <label>To <input type="date" id="report-to" value="${reportDateTo}"></label>
        <button class="btn btn-sm btn-secondary" id="apply-report-filter">Apply</button>
        <button class="btn btn-sm btn-secondary" id="clear-report-filter">Clear</button>
      </div>
    </div>
    <nav class="report-tabs" id="report-tabs">
      <button class="report-tab ${reportSection === 'financial' ? 'active' : ''}" data-section="financial">💰 Financial</button>
      <button class="report-tab ${reportSection === 'sales' ? 'active' : ''}" data-section="sales">📊 Sales</button>
      <button class="report-tab ${reportSection === 'purchasing' ? 'active' : ''}" data-section="purchasing">🛒 Purchasing</button>
      <button class="report-tab ${reportSection === 'inventory' ? 'active' : ''}" data-section="inventory">📦 Inventory</button>
      <button class="report-tab ${reportSection === 'operations' ? 'active' : ''}" data-section="operations">⚙ Operations</button>
    </nav>
    <div id="report-body"><div class="text-muted">Loading reports...</div></div>
  `;

  async function loadReports() {
    $('#report-body').innerHTML = '<div class="text-muted">Loading reports...</div>';
    const params = new URLSearchParams();
    if (reportDateFrom) params.set('from', reportDateFrom);
    if (reportDateTo) params.set('to', reportDateTo);
    const qs = params.toString();
    reportData = await api(`reports/full${qs ? '?' + qs : ''}`);
    renderReportSection();
  }

  $('#report-tabs').querySelectorAll('.report-tab').forEach(tab => {
    tab.onclick = () => {
      reportSection = tab.dataset.section;
      $('#report-tabs').querySelectorAll('.report-tab').forEach(t => t.classList.toggle('active', t.dataset.section === reportSection));
      renderReportSection();
    };
  });

  $('#apply-report-filter').onclick = () => {
    reportDateFrom = $('#report-from').value;
    reportDateTo = $('#report-to').value;
    loadReports();
  };
  $('#clear-report-filter').onclick = () => {
    reportDateFrom = reportDateTo = '';
    $('#report-from').value = $('#report-to').value = '';
    loadReports();
  };
  $('#refresh-reports').onclick = loadReports;
  $('#print-reports').onclick = () => window.print();

  await loadReports();
}
