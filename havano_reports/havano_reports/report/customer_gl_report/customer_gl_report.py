# Copyright (c) 2025, nasirucode and contributors
# For license information, please see license.txt

# import frappe

import frappe
from frappe import _
from frappe.utils import flt, getdate, cstr
from erpnext.accounts.utils import get_balance_on
from erpnext.accounts.report.utils import get_currency, convert_to_presentation_currency

def execute(filters=None):
    if not filters:
        filters = {}
    
    columns = get_columns(filters)
    data = get_data(filters)
    
    return columns, data

def get_columns(filters):
    """Return columns for the report"""
    columns = [
        {
            "fieldname": "posting_date",
            "fieldtype": "Date",
            "label": _("Posting Date"),
            "width": 100
        },
        {
            "fieldname": "voucher_type",
            "fieldtype": "Data",
            "label": _("Voucher Type"),
            "width": 120
        },
        {
            "fieldname": "voucher_no",
            "fieldtype": "Dynamic Link",
            "label": _("Voucher No"),
            "options": "voucher_type",
            "width": 180
        }
    ]
    
    # Add transaction currency columns if requested
    if filters.get("add_values_in_transaction_currency"):
        columns.extend([
            {
                "fieldname": "debit_in_account_currency",
                "fieldtype": "Float",
                "label": _("Debit in Transaction Currency"),
                "width": 150
            },
            {
                "fieldname": "credit_in_account_currency",
                "fieldtype": "Float",
                "label": _("Credit in Transaction Currency"),
                "width": 150
            },
            {
                "fieldname": "account_currency",
                "fieldtype": "Data",
                "label": _("Currency"),
                "width": 80
            }
        ])
    
    # Add main currency columns
    currency = filters.get("presentation_currency") or "USD"
    columns.extend([
        {
            "fieldname": "debit",
            "fieldtype": "Float",
            "label": _("Debit ({0})").format(currency),
            "width": 130
        },
        {
            "fieldname": "credit",
            "fieldtype": "Float",
            "label": _("Credit ({0})").format(currency),
            "width": 130
        },
        {
            "fieldname": "balance",
            "fieldtype": "Float",
            "label": _("Balance ({0})").format(currency),
            "width": 130
        }
    ])
    
    # Add remarks column if requested
    if filters.get("show_remarks"):
        columns.append({
            "fieldname": "remarks",
            "fieldtype": "Data",
            "label": _("Remarks"),
            "width": 200
        })
    
    return columns

def get_data(filters):
    """Get GL Entry data based on filters"""
    conditions = get_conditions(filters)
    
    # Build select fields
    select_fields = """
        gle.posting_date,
        gle.voucher_type,
        gle.voucher_no,
        gle.debit,
        gle.credit,
        gle.account,
        gle.party_type,
        gle.party,
        gle.company,
        gle.cost_center,
        gle.project,
        gle.debit_in_account_currency,
        gle.credit_in_account_currency,
        gle.account_currency
    """
    
    if filters.get("show_remarks"):
        select_fields += ", gle.remarks"
    
    gl_entries = frappe.db.sql("""
        SELECT {select_fields}
        FROM `tabGL Entry` gle
        WHERE {conditions}
        ORDER BY gle.posting_date, gle.creation
    """.format(select_fields=select_fields, conditions=conditions), filters, as_dict=1)
    
    # Process net values for party accounts if requested
    if filters.get("show_net_values_in_party_account") and filters.get("party"):
        gl_entries = process_net_values(gl_entries, filters)
    
    # Calculate running balance
    data = []
    running_balance = 0.0
    
    # Get opening balance if required
    if filters.get("show_opening_entries"):
        opening_balance = get_opening_balance(filters)
        if opening_balance:
            running_balance = opening_balance
            opening_entry = {
                "posting_date": getdate(filters.get("from_date")),
                "voucher_type": "",
                "voucher_no": _("Opening Balance"),
                "debit": opening_balance if opening_balance > 0 else 0,
                "credit": abs(opening_balance) if opening_balance < 0 else 0,
                "balance": opening_balance
            }
            
            if filters.get("add_values_in_transaction_currency"):
                opening_entry.update({
                    "debit_in_account_currency": opening_balance if opening_balance > 0 else 0,
                    "credit_in_account_currency": abs(opening_balance) if opening_balance < 0 else 0,
                    "account_currency": filters.get("presentation_currency", "USD")
                })
            
            if filters.get("show_remarks"):
                opening_entry["remarks"] = _("Opening Balance")
            
            data.append(opening_entry)
    
    # Process GL entries
    if filters.get("group_by") == "Group by Voucher (Consolidated)":
        data.extend(get_consolidated_data(gl_entries, running_balance, filters))
    else:
        for entry in gl_entries:
            running_balance += flt(entry.debit) - flt(entry.credit)
            
            row_data = {
                "posting_date": entry.posting_date,
                "voucher_type": entry.voucher_type,
                "voucher_no": entry.voucher_no,
                "debit": flt(entry.debit),
                "credit": flt(entry.credit),
                "balance": running_balance
            }
            
            if filters.get("add_values_in_transaction_currency"):
                row_data.update({
                    "debit_in_account_currency": flt(entry.debit_in_account_currency),
                    "credit_in_account_currency": flt(entry.credit_in_account_currency),
                    "account_currency": entry.account_currency
                })
            
            if filters.get("show_remarks"):
                row_data["remarks"] = entry.get("remarks", "")
            
            data.append(row_data)
    
    return data

def get_conditions(filters):
    """Build WHERE conditions based on filters"""
    conditions = []
    
    # Include cancelled entries or not
    if filters.get("show_cancelled_entries"):
        conditions.append("gle.docstatus IN (1, 2)")
    else:
        conditions.append("gle.docstatus = 1")
    
    if filters.get("company"):
        conditions.append("gle.company = %(company)s")
    
    if filters.get("from_date"):
        conditions.append("gle.posting_date >= %(from_date)s")
    
    if filters.get("to_date"):
        conditions.append("gle.posting_date <= %(to_date)s")
    
    if filters.get("account"):
        if isinstance(filters.get("account"), list) and filters.get("account"):
            conditions.append("gle.account IN %(account)s")
        elif filters.get("account"):
            conditions.append("gle.account = %(account)s")
    
    if filters.get("party_type"):
        conditions.append("gle.party_type = %(party_type)s")
    
    if filters.get("party"):
        if isinstance(filters.get("party"), list) and filters.get("party"):
            conditions.append("gle.party IN %(party)s")
        elif filters.get("party"):
            conditions.append("gle.party = %(party)s")
    
    if filters.get("cost_center"):
        if isinstance(filters.get("cost_center"), list) and filters.get("cost_center"):
            conditions.append("gle.cost_center IN %(cost_center)s")
        elif filters.get("cost_center"):
            conditions.append("gle.cost_center = %(cost_center)s")
    
    if filters.get("project"):
        if isinstance(filters.get("project"), list) and filters.get("project"):
            conditions.append("gle.project IN %(project)s")
        elif filters.get("project"):
            conditions.append("gle.project = %(project)s")
    
    # Ignore Exchange Rate Revaluation Journals
    if filters.get("ignore_err"):
        conditions.append("gle.voucher_type != 'Exchange Rate Revaluation'")
    
    # Ignore System Generated Credit/Debit Notes
    if filters.get("ignore_system_generated_entries"):
        conditions.append("""
            NOT (gle.voucher_type IN ('Sales Invoice', 'Purchase Invoice') 
            AND gle.against_voucher_type IN ('Sales Invoice', 'Purchase Invoice')
            AND gle.is_system_generated = 1)
        """)
    
    return " AND ".join(conditions) if conditions else "1=1"

def get_opening_balance(filters):
    """Calculate opening balance"""
    if not filters.get("account") or not filters.get("from_date"):
        return 0.0
    
    accounts = filters.get("account")
    if not isinstance(accounts, list):
        accounts = [accounts] if accounts else []
    
    opening_balance = 0.0
    for account in accounts:
        balance = get_balance_on(
            account=account,
            date=getdate(filters.get("from_date")) - 1,
            party_type=filters.get("party_type"),
            party=filters.get("party")[0] if isinstance(filters.get("party"), list) and filters.get("party") else filters.get("party"),
            company=filters.get("company"),
            cost_center=filters.get("cost_center")[0] if isinstance(filters.get("cost_center"), list) and filters.get("cost_center") else filters.get("cost_center"),
            project=filters.get("project")[0] if isinstance(filters.get("project"), list) and filters.get("project") else filters.get("project")
        )
        opening_balance += flt(balance)
    
    return opening_balance

def get_consolidated_data(gl_entries, running_balance, filters):
    """Group entries by voucher and consolidate"""
    voucher_map = {}
    
    # Group by voucher
    for entry in gl_entries:
        key = f"{entry.voucher_type}::{entry.voucher_no}::{entry.posting_date}"
        if key not in voucher_map:
            voucher_map[key] = {
                "posting_date": entry.posting_date,
                "voucher_type": entry.voucher_type,
                "voucher_no": entry.voucher_no,
                "debit": 0,
                "credit": 0,
                "debit_in_account_currency": 0,
                "credit_in_account_currency": 0,
                "account_currency": entry.get("account_currency", ""),
                "remarks": []
            }
        
        voucher_map[key]["debit"] += flt(entry.debit)
        voucher_map[key]["credit"] += flt(entry.credit)
        voucher_map[key]["debit_in_account_currency"] += flt(entry.get("debit_in_account_currency", 0))
        voucher_map[key]["credit_in_account_currency"] += flt(entry.get("credit_in_account_currency", 0))
        
        if filters.get("show_remarks") and entry.get("remarks"):
            voucher_map[key]["remarks"].append(entry.get("remarks"))
    
    # Convert to list and calculate balance
    data = []
    for voucher_data in sorted(voucher_map.values(), key=lambda x: (x["posting_date"], x["voucher_type"], x["voucher_no"])):
        running_balance += flt(voucher_data["debit"]) - flt(voucher_data["credit"])
        voucher_data["balance"] = running_balance
        
        if filters.get("show_remarks"):
            voucher_data["remarks"] = "; ".join(set(voucher_data["remarks"]))
        
        data.append(voucher_data)
    
    return data

def process_net_values(gl_entries, filters):
    """Process net values for party accounts"""
    if not filters.get("party"):
        return gl_entries
    
    # Group entries by voucher and calculate net values
    voucher_groups = {}
    for entry in gl_entries:
        key = f"{entry.voucher_type}::{entry.voucher_no}"
        if key not in voucher_groups:
            voucher_groups[key] = []
        voucher_groups[key].append(entry)
    
    processed_entries = []
    for voucher_entries in voucher_groups.values():
        net_debit = sum(flt(e.debit) for e in voucher_entries)
        net_credit = sum(flt(e.credit) for e in voucher_entries)
        
        if net_debit != net_credit:
            # Keep one entry with net values
            entry = voucher_entries[0].copy()
            entry.debit = max(0, net_debit - net_credit)
            entry.credit = max(0, net_credit - net_debit)
            processed_entries.append(entry)
    
    return processed_entries

