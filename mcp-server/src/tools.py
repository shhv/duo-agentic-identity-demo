"""Tool definitions and mock implementations for MCP server."""

import json
import uuid
from datetime import date

from .mock_data import (
    BUDGETS,
    DEPARTMENTS,
    EMPLOYEES,
    EXPENSES,
    PENDING_PAYMENTS,
)

TOOL_DEFINITIONS = [
    {
        "name": "hr_get_employee",
        "description": "Get detailed employee information by employee ID.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "employee_id": {
                    "type": "string",
                    "description": "Employee ID (e.g. EMP001)",
                }
            },
            "required": ["employee_id"],
        },
    },
    {
        "name": "hr_list_departments",
        "description": "List all departments with headcount and leadership info.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "hr_create_employee",
        "description": "Create a new employee record in the HR system.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Full name"},
                "email": {"type": "string", "description": "Email address"},
                "department": {"type": "string", "description": "Department name"},
                "title": {"type": "string", "description": "Job title"},
                "salary": {"type": "number", "description": "Annual salary"},
            },
            "required": ["name", "email", "department", "title", "salary"],
        },
    },
    {
        "name": "hr_update_salary",
        "description": "Update an employee's salary. Requires HR write access.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "employee_id": {"type": "string", "description": "Employee ID"},
                "new_salary": {"type": "number", "description": "New annual salary"},
                "reason": {"type": "string", "description": "Reason for change"},
            },
            "required": ["employee_id", "new_salary", "reason"],
        },
    },
    {
        "name": "finance_get_budget",
        "description": "Get budget details for a department by budget code.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "budget_code": {
                    "type": "string",
                    "description": "Budget code (e.g. ENG-2024)",
                }
            },
            "required": ["budget_code"],
        },
    },
    {
        "name": "finance_list_expenses",
        "description": "List recent expense reports, optionally filtered by department.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "department": {
                    "type": "string",
                    "description": "Filter by department name (optional)",
                }
            },
        },
    },
    {
        "name": "finance_create_expense",
        "description": "Submit a new expense report for approval.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "submitted_by": {"type": "string", "description": "Employee ID"},
                "department": {"type": "string", "description": "Department name"},
                "amount": {"type": "number", "description": "Expense amount in USD"},
                "description": {"type": "string", "description": "Expense description"},
                "category": {"type": "string", "description": "Budget category"},
            },
            "required": ["submitted_by", "department", "amount", "description", "category"],
        },
    },
    {
        "name": "finance_approve_payment",
        "description": "Approve a pending payment. Requires Finance write access.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "payment_id": {"type": "string", "description": "Payment ID (e.g. PAY001)"},
                "approver_id": {"type": "string", "description": "Approver's employee ID"},
            },
            "required": ["payment_id", "approver_id"],
        },
    },
]


async def hr_get_employee(employee_id: str) -> dict:
    emp = EMPLOYEES.get(employee_id)
    if not emp:
        raise ValueError(f"Employee not found: {employee_id}")
    return emp


async def hr_list_departments() -> dict:
    return {"departments": DEPARTMENTS}


async def hr_create_employee(name: str, email: str, department: str, title: str, salary: float) -> dict:
    new_id = f"EMP{len(EMPLOYEES) + 1:03d}"
    record = {
        "id": new_id,
        "name": name,
        "email": email,
        "department": department,
        "title": title,
        "salary": salary,
        "start_date": date.today().isoformat(),
        "manager": None,
    }
    EMPLOYEES[new_id] = record
    return {"created": record}


async def hr_update_salary(employee_id: str, new_salary: float, reason: str) -> dict:
    emp = EMPLOYEES.get(employee_id)
    if not emp:
        raise ValueError(f"Employee not found: {employee_id}")
    old_salary = emp["salary"]
    emp["salary"] = new_salary
    return {
        "employee_id": employee_id,
        "old_salary": old_salary,
        "new_salary": new_salary,
        "reason": reason,
        "effective_date": date.today().isoformat(),
    }


async def finance_get_budget(budget_code: str) -> dict:
    budget = BUDGETS.get(budget_code)
    if not budget:
        raise ValueError(f"Budget not found: {budget_code}")
    return budget


async def finance_list_expenses(department: str | None = None) -> dict:
    results = EXPENSES
    if department:
        results = [e for e in results if e["department"] == department]
    return {"expenses": results}


async def finance_create_expense(
    submitted_by: str, department: str, amount: float, description: str, category: str
) -> dict:
    new_expense = {
        "id": f"EXP{len(EXPENSES) + 1:03d}",
        "submitted_by": submitted_by,
        "department": department,
        "amount": amount,
        "description": description,
        "category": category,
        "status": "pending",
        "date": date.today().isoformat(),
    }
    EXPENSES.append(new_expense)
    return {"created": new_expense}


async def finance_approve_payment(payment_id: str, approver_id: str) -> dict:
    payment = next((p for p in PENDING_PAYMENTS if p["id"] == payment_id), None)
    if not payment:
        raise ValueError(f"Payment not found: {payment_id}")
    payment["status"] = "approved"
    payment["approved_by"] = approver_id
    payment["approved_date"] = date.today().isoformat()
    return {"approved": payment}


async def dispatch_tool(name: str, arguments: dict) -> dict:
    """Dispatch a tool call to the appropriate handler."""
    handlers = {
        "hr_get_employee": lambda args: hr_get_employee(args["employee_id"]),
        "hr_list_departments": lambda args: hr_list_departments(),
        "hr_create_employee": lambda args: hr_create_employee(
            args["name"], args["email"], args["department"], args["title"], args["salary"]
        ),
        "hr_update_salary": lambda args: hr_update_salary(
            args["employee_id"], args["new_salary"], args["reason"]
        ),
        "finance_get_budget": lambda args: finance_get_budget(args["budget_code"]),
        "finance_list_expenses": lambda args: finance_list_expenses(args.get("department")),
        "finance_create_expense": lambda args: finance_create_expense(
            args["submitted_by"], args["department"], args["amount"],
            args["description"], args["category"]
        ),
        "finance_approve_payment": lambda args: finance_approve_payment(
            args["payment_id"], args["approver_id"]
        ),
    }

    handler = handlers.get(name)
    if handler is None:
        raise ValueError(f"Unknown tool: {name}")

    return await handler(arguments)
