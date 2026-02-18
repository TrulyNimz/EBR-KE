"""
Workflow Conditions Evaluation.

Evaluates JSON-based condition expressions for workflow transitions.
"""
from typing import Any, Dict


def evaluate_conditions(conditions: Dict, record) -> bool:
    """
    Evaluate workflow conditions against a record.

    Supports a subset of JSON Logic for condition evaluation.

    Args:
        conditions: JSON logic expression
        record: The Django model instance

    Returns:
        True if conditions are met, False otherwise.
    """
    if not conditions:
        return True

    return _evaluate(conditions, _get_record_data(record))


def _get_record_data(record) -> Dict[str, Any]:
    """Extract data from a record for condition evaluation."""
    data = {}

    # Try to get dict representation
    if hasattr(record, 'to_dict'):
        data = record.to_dict()
    elif hasattr(record, '__dict__'):
        for key, value in record.__dict__.items():
            if not key.startswith('_'):
                data[key] = value

    # Add common computed values
    data['_id'] = str(record.pk)
    if hasattr(record, 'status'):
        data['_status'] = record.status
    if hasattr(record, 'created_at'):
        data['_created_at'] = record.created_at

    return data


def _evaluate(expression: Any, data: Dict) -> Any:
    """
    Recursively evaluate a JSON logic expression.

    Supports operators:
    - and, or, not (boolean logic)
    - ==, !=, <, >, <=, >= (comparison)
    - in, contains (membership)
    - var (variable access)
    - if (conditional)
    """
    if not isinstance(expression, dict):
        return expression

    # Get the operator
    operator = list(expression.keys())[0]
    args = expression[operator]

    # Ensure args is a list
    if not isinstance(args, list):
        args = [args]

    # Boolean operators
    if operator == 'and':
        return all(_evaluate(arg, data) for arg in args)

    elif operator == 'or':
        return any(_evaluate(arg, data) for arg in args)

    elif operator == 'not':
        return not _evaluate(args[0], data)

    # Comparison operators
    elif operator == '==':
        return _evaluate(args[0], data) == _evaluate(args[1], data)

    elif operator == '!=':
        return _evaluate(args[0], data) != _evaluate(args[1], data)

    elif operator == '<':
        return _evaluate(args[0], data) < _evaluate(args[1], data)

    elif operator == '>':
        return _evaluate(args[0], data) > _evaluate(args[1], data)

    elif operator == '<=':
        return _evaluate(args[0], data) <= _evaluate(args[1], data)

    elif operator == '>=':
        return _evaluate(args[0], data) >= _evaluate(args[1], data)

    # Membership operators
    elif operator == 'in':
        value = _evaluate(args[0], data)
        collection = _evaluate(args[1], data)
        return value in collection

    elif operator == 'contains':
        collection = _evaluate(args[0], data)
        value = _evaluate(args[1], data)
        if isinstance(collection, str):
            return value in collection
        return value in collection

    # Variable access
    elif operator == 'var':
        var_name = args[0] if isinstance(args, list) else args
        default = args[1] if isinstance(args, list) and len(args) > 1 else None
        return _get_var(data, var_name, default)

    # Conditional
    elif operator == 'if':
        # args: [condition, then_value, else_value]
        condition = _evaluate(args[0], data)
        if condition:
            return _evaluate(args[1], data) if len(args) > 1 else True
        else:
            return _evaluate(args[2], data) if len(args) > 2 else False

    # Missing operator (check if variable exists and is truthy)
    elif operator == 'missing':
        for var_name in args:
            value = _get_var(data, var_name, None)
            if value is None or value == '':
                return True
        return False

    # All operator (check if all items in array match)
    elif operator == 'all':
        array = _evaluate(args[0], data)
        condition_template = args[1]
        if not isinstance(array, list):
            return False
        for item in array:
            item_data = {**data, '_item': item}
            if not _evaluate(condition_template, item_data):
                return False
        return True

    # Some operator (check if any item matches)
    elif operator == 'some':
        array = _evaluate(args[0], data)
        condition_template = args[1]
        if not isinstance(array, list):
            return False
        for item in array:
            item_data = {**data, '_item': item}
            if _evaluate(condition_template, item_data):
                return True
        return False

    # Arithmetic operators
    elif operator == '+':
        return sum(_evaluate(arg, data) for arg in args)

    elif operator == '-':
        if len(args) == 1:
            return -_evaluate(args[0], data)
        return _evaluate(args[0], data) - _evaluate(args[1], data)

    elif operator == '*':
        result = 1
        for arg in args:
            result *= _evaluate(arg, data)
        return result

    elif operator == '/':
        dividend = _evaluate(args[0], data)
        divisor = _evaluate(args[1], data)
        if divisor == 0:
            return None
        return dividend / divisor

    # Unknown operator
    return None


def _get_var(data: Dict, var_name: str, default: Any = None) -> Any:
    """
    Get a variable value from data, supporting dot notation.

    Example: "user.email" gets data['user']['email']
    """
    if not var_name:
        return data

    parts = var_name.split('.')
    value = data

    for part in parts:
        if isinstance(value, dict):
            value = value.get(part)
        elif hasattr(value, part):
            value = getattr(value, part)
        else:
            return default

        if value is None:
            return default

    return value


# Example conditions for reference:
EXAMPLE_CONDITIONS = {
    # Simple equality
    'status_is_draft': {'==': [{'var': 'status'}, 'draft']},

    # Multiple conditions (AND)
    'ready_for_review': {
        'and': [
            {'==': [{'var': 'status'}, 'in_progress']},
            {'>': [{'var': 'completion_percentage'}, 90]},
            {'not': {'missing': ['reviewer_id']}}
        ]
    },

    # Any of conditions (OR)
    'can_approve': {
        'or': [
            {'==': [{'var': 'user_role'}, 'supervisor']},
            {'==': [{'var': 'user_role'}, 'manager']},
            {'in': ['approver', {'var': 'user_permissions'}]}
        ]
    },

    # Nested conditions
    'complex_approval': {
        'if': [
            {'>': [{'var': 'amount'}, 10000]},
            {'==': [{'var': 'approver_level'}, 'executive']},
            {'>=': [{'var': 'approver_level'}, 'manager']}
        ]
    }
}
