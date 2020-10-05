OneBeat integration
===================

Setup
-----

Is needed to enable the `Storage Locations` and `Multi-Warehouses` in the `Inventory`/`Configuration`/`Settings`

**Files**

STOCKLOCATIONS
--------------
* Nombre del archivo: STOCKLOCATIONS_postfix.csv
* postfix: YYYYMMDD_HHMM
* Carpeta para dejarlo: C:\OneBeatFolders\inputFolder\


```python
for warehouse in stock.warehouse if warehouse.to_report
```

```python
{
    'Nombre Agencia': warehouse.lot_stock_id.name,
    'Descripción': warehouse.name,
    'Año reporte': now.year,
    'Mes Reporte': now.month,
    'Dia Reporte': now.day,
    'Ubicación': None,
}
```

MTSSKUS
-------
* Nombre del archivo: MTSSKUS_postfix.csv
* postfix: YYYYMMDD_HHMM
* Carpeta para dejarlo: C:\OneBeatFolders\inputFolder\

```python
for warehouse in stock.locations for product in product.product if product.sale_ok
```

```python
{
    'Stock Location Name': 'warehouse.name',
    'Origin SL': 'Proveedor' if product.seller_ids else '' # TODO
    'SKU Name': product.default_code,
    'SKU Description': product.name,
    'Buffer Size': product.buffer_size, # TODO make field
    'Replenishment Time': product.seller_ids[0].delay if product.seller_ids else '' # TODO
    'Inventory at Site': 0,
    'Inventory at Transit': 0,
    'Inventory at Production': 0,
    'Precio unitario': product.list_price,
    'TVC': product.standard_price,
    'Throughput': product.list_price - product.standard_price,
    'Minimo Reabastecimiento': None,
    'Unidad de Medida': product.uom_id.name,
    'Reported Year': now.year,
    'Reported Month': now.month,
    'Reported Day': now.day,
}
```

TRANSACTIONS
------------
* Nombre del archivo: TRANSACTIONS_postfix.csv
* postfix: YYYYMMDD_HHMM
* Carpeta para dejarlo: C:\OneBeatFolders\inputFolder\

```python
for move in stock.move if move.location_id.to_check or move.location_dest_id.to_check
```

```python
{
    'Origin': move.location_id.name,
    'SKU Name': move.product_id.default_code,
    'Destination': move.location_dest_id.name,
    'Transaction Type (in/out)': 'OUT' if move.location_id.usage == 'internal' else 'IN',
    'Quantity': move.quantity_done,
    'Shipping Year': now.year,
    'Shipping Month': now.month,
    'Shipping Day': now.day,
}
```

STATUS
------
* Nombre del archivo: STATUS_postfix.csv
* postfix: YYYYMMDD_HHMM
* Carpeta para dejarlo: C:\OneBeatFolders\inputFolder\

```python
for warehouse in stock.locations for product in product.product if product.sale_ok
```

```python
{
    'Stock Location Name': warehouse.name,
    'SKU Name': product.default_code,
    'Inventory At Hand': sum(quant.quantity for stock.quant if location_id == warehouse and quant.product_id == product_id),
    'Inventory On The Way': sum(line.product_qty for stock.move.line if line.location_id == warehouse line.state not in ['done', 'draft']),
    'Report Year': now.year,
    'Report Month': now.month,
    'Report Day': now.day,
}
```
