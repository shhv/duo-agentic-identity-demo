# Duo Admin Panel Setup

This guide walks through configuring Duo SSO and Authorization policies for the demo.

## Prerequisites

- Duo Admin Panel access (admin.duosecurity.com)
- Duo SSO enabled for your organization
- Duo Authorization Connector alpha access

## Step 1: Create Agent Applications

In Duo Admin → **Applications** → **Protect an Application**:

### HR Agent Application
1. Search for "OAuth 2.0 Client Credentials"
2. Create application named: `hr-agent-demo`
3. Note the **Client ID** and **Client Secret**
4. Set allowed grant types: `client_credentials`

### Finance Agent Application
1. Repeat for `finance-agent-demo`
2. Note credentials separately

## Step 2: Create Groups

In Duo Admin → **Groups**:

| Group Name | Members |
|------------|---------|
| All Agents | hr-agent-demo, finance-agent-demo |
| HR Team | hr-agent-demo |
| Finance Team | finance-agent-demo |

## Step 3: Register the MCP Server

In the Authorization Connector section of Duo Admin:

1. Register a new **Protected Resource** for your MCP server
2. Name: `acme-mcp-tools`
3. Add all 8 tool names as resource identifiers

## Step 4: Create Authorization Policies

### Policy: Shared Read Access
- **Who:** All Agents group
- **Can access:** `hr_get_employee`, `hr_list_departments`, `finance_get_budget`, `finance_list_expenses`
- **Effect:** Allow

### Policy: HR Write Access
- **Who:** HR Team group
- **Can access:** `hr_create_employee`, `hr_update_salary`
- **Effect:** Allow

### Policy: Finance Write Access
- **Who:** Finance Team group
- **Can access:** `finance_create_expense`, `finance_approve_payment`
- **Effect:** Allow

## Step 5: Create Authorization Connector API Credentials

In Duo Admin → **Applications**:

1. Find or create the "Authorization Connector" application
2. Note the **API Hostname**, **Integration Key**, and **Secret Key**
3. These go into `.env` as `DUO_API_HOSTNAME`, `DUO_INTEGRATION_KEY`, `DUO_SECRET_KEY`

## Expected Result

| Agent | Visible Tools | Allowed | Denied |
|-------|--------------|---------|--------|
| HR Agent | 6 of 8 | hr_get_employee, hr_list_departments, hr_create_employee, hr_update_salary, finance_get_budget, finance_list_expenses | finance_create_expense, finance_approve_payment |
| Finance Agent | 6 of 8 | hr_get_employee, hr_list_departments, finance_get_budget, finance_list_expenses, finance_create_expense, finance_approve_payment | hr_create_employee, hr_update_salary |
