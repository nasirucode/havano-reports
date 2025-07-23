// Copyright (c) 2025, nasirucode and contributors
// For license information, please see license.txt

frappe.query_reports["Customer GL Report"] = {
    "filters": [
        {
            "fieldname": "company",
            "label": __("Company"),
            "fieldtype": "Link",
            "options": "Company",
            "default": frappe.defaults.get_user_default("Company"),
            "reqd": 1
        },
        {
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
            "reqd": 1,
            "width": "60px"
        },
        {
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.get_today(),
            "reqd": 1,
            "width": "60px"
        },
        {
            "fieldname": "account",
            "label": __("Account"),
            "fieldtype": "MultiSelectList",
            "options": "Account",
            "get_data": function(txt) {
                return frappe.db.get_link_options('Account', txt, {
                    company: frappe.query_report.get_filter_value("company")
                });
            }
        },
        {
            "fieldname": "party_type",
            "label": __("Party Type"),
            "fieldtype": "Select",
            "options": ["", "Customer", "Supplier", "Employee", "Member", "Shareholder", "Student"],
            "default": "Customer"
        },
        {
            "fieldname": "party",
            "label": __("Party"),
            "fieldtype": "MultiSelectList",
            "get_data": function(txt) {
                if (!frappe.query_report.get_filter_value('party_type')) {
                    frappe.throw(__("Please select Party Type first"));
                }
                return frappe.db.get_link_options(frappe.query_report.get_filter_value('party_type'), txt);
            }
        },
        {
            "fieldname": "party_name",
            "label": __("Party Name"),
            "fieldtype": "Data",
            "hidden": 1
        },
        {
            "fieldname": "group_by",
            "label": __("Group by"),
            "fieldtype": "Select",
            "options": [
                "",
                "Group by Voucher (Consolidated)",
                "Group by Account"
            ],
            "default": "Group by Voucher (Consolidated)"
        },
        {
            "fieldname": "cost_center",
            "label": __("Cost Center"),
            "fieldtype": "MultiSelectList",
            "options": "Cost Center",
            "get_data": function(txt) {
                return frappe.db.get_link_options('Cost Center', txt, {
                    company: frappe.query_report.get_filter_value("company")
                });
            }
        },
        {
            "fieldname": "project",
            "label": __("Project"),
            "fieldtype": "MultiSelectList",
            "options": "Project"
        },
        {
            "fieldname": "presentation_currency",
            "label": __("Currency"),
            "fieldtype": "Link",
            "options": "Currency",
            "default": "USD"
        },
        {
            "fieldname": "include_dimensions",
            "label": __("Include Dimensions"),
            "fieldtype": "Check",
            "default": 1
        },
        {
            "fieldname": "show_opening_entries",
            "label": __("Show Opening Entries"),
            "fieldtype": "Check",
            "default": 1
        },
        {
            "fieldname": "include_default_book_entries",
            "label": __("Include Default Book Entries"),
            "fieldtype": "Check",
            "default": 1
        },
        {
            "fieldname": "show_cancelled_entries",
            "label": __("Show Cancelled Entries"),
            "fieldtype": "Check",
            "default": 0
        },
        {
            "fieldname": "show_net_values_in_party_account",
            "label": __("Show Net Values in Party Account"),
            "fieldtype": "Check",
            "default": 0
        },
        {
            "fieldname": "add_values_in_transaction_currency",
            "label": __("Add Columns in Transaction Currency"),
            "fieldtype": "Check",
            "default": 0
        },
        {
            "fieldname": "show_remarks",
            "label": __("Show Remarks"),
            "fieldtype": "Check",
            "default": 0
        },
        {
            "fieldname": "ignore_err",
            "label": __("Ignore Exchange Rate Revaluation Journals"),
            "fieldtype": "Check",
            "default": 0
        },
        {
            "fieldname": "ignore_system_generated_entries",
            "label": __("Ignore System Generated Credit / Debit Notes"),
            "fieldtype": "Check",
            "default": 0
        }
    ],

    "formatter": function (value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        console.log(data.voucher_no)

        // Format debit columns (both currencies)
        if ((column.fieldname == "debit" || column.fieldname == "debit_in_account_currency") && data && flt(data[column.fieldname]) > 0) {
            value = "<span style='color:green; font-weight: bold;'>" + value + "</span>";
        }
        // Format credit columns (both currencies)
        else if ((column.fieldname == "credit" || column.fieldname == "credit_in_account_currency") && data && flt(data[column.fieldname]) > 0) {
            value = "<span style='color:red; font-weight: bold;'>" + value + "</span>";
        }
        // Format balance column
        else if (column.fieldname == "balance") {
            if (data && flt(data.balance) > 0) {
                value = "<span style='color:green; font-weight: bold;'>" + value + "</span>";
            } else if (data && flt(data.balance) < 0) {
                value = "<span style='color:red; font-weight: bold;'>" + value + "</span>";
            }
        }
        // Format voucher_no as link
        else if (column.fieldname == "voucher_no" && data && data.voucher_type && data.voucher_no) {
            if (data.voucher_no != __("Opening Balance")) {
                value = `<a href="/app/${data.voucher_type.toLowerCase().replace(/ /g, "-")}/${data.voucher_no}" target="_blank">${data.voucher_no}</a>`;
            }
        }
        // Highlight cancelled entries
        if (data && data.docstatus == 2) {
            value = "<span style='color: #d1d1d1; text-decoration: line-through;'>" + value + "</span>";
        }

        return value;
    },

    "onload": function(report) {
        // Set default filters based on your requirements
        report.page.add_inner_button(__("Export"), function() {
            frappe.query_report.export_report();
        });

        // Add refresh button
        report.page.add_inner_button(__("Refresh"), function() {
            frappe.query_report.refresh();
        });

        // Show/hide transaction currency columns based on checkbox
        frappe.query_report.get_filter('add_values_in_transaction_currency').on('change', function() {
            frappe.query_report.refresh();
        });

        // Show/hide remarks column based on checkbox
        frappe.query_report.get_filter('show_remarks').on('change', function() {
            frappe.query_report.refresh();
        });
    },

    "get_datatable_options": function(options) {
        return Object.assign(options, {
            checkboxColumn: true,
            events: {
                onCheckRow: function(data) {
                    // Handle row selection if needed
                }
            }
        });
    }
};
