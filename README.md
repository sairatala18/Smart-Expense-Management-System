# Smart Expense Management System

## Overview

The Smart Expense Management System is a web-based application designed to simplify the process of submitting, tracking, and approving employee expenses. Employees can upload expense claims with supporting documents, while managers can review, approve, or reject requests through a centralized dashboard.

## Problem Statement

Managing employee expenses manually can be time-consuming and prone to errors. This system provides a structured workflow that improves transparency, reduces paperwork, and helps organizations track expenses efficiently.

## Key Features

### Employee Module
- Employee Registration with Company Code
- Secure Login System
- Submit Expense Requests
- Upload Bill Proofs (Image/PDF)
- View Expense Status
- View Rejection Comments from Manager
- Track Expense History

### Manager Module
- Secure Manager Login
- Approve or Reject Employee Registrations
- Generate Employee IDs
- View Employee Details
- Manage Employees
- Approve or Reject Expense Requests
- Add Comments for Rejected Expenses
- View Past Expenses
- Dashboard Analytics and Statistics
- Search and Filter Employees

## Workflow

1. Employee registers using the company code.
2. Manager reviews and approves the registration.
3. Employee receives an Employee ID.
4. Employee submits expense claims with proof.
5. Manager reviews the submitted expenses.
6. Manager approves or rejects the request.
7. If rejected, the employee can view the manager's comments.
8. All records are maintained for future tracking and reporting.

## Technologies Used

- Python
- Flask
- HTML
- CSS
- JavaScript
- CSV File Storage

## Project Structure

```text
Expense_app/
│
├── app.py
├── employees.csv
├── expenses.csv
├── uploads/
├── templates/
│   ├── employee.html
│   ├── manager.html
│   ├── employee_login.html
│   ├── employee_register.html
│   └── partials/
│
└── migrate.py
```

## Future Enhancements

- Database Integration (MySQL)
- Email Notifications
- Expense Reports and Analytics
- Export Reports to PDF/Excel
- Multi-Level Approval Workflow
- Mobile Responsive Design

## Author

Ratala Sai Kiran

## GitHub Repository

Smart Expense Management System – Expense Approval and Employee Management Platform
