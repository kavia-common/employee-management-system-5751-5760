#!/bin/bash
cd /home/kavia/workspace/code-generation/employee-management-system-5751-5760/employee_backend
source venv/bin/activate
flake8 .
LINT_EXIT_CODE=$?
if [ $LINT_EXIT_CODE -ne 0 ]; then
  exit 1
fi

