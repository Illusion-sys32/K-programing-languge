# k_interpreter.py

import ast
import operator
import re

class KInterpreter:
    def __init__(self):
        self.global_variables = {}
        self.local_variables_stack = []  # Stack to handle nested scopes
        # Define supported operators for safe evaluation
        self.operators = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.Mod: operator.mod,
            ast.Pow: operator.pow,
            ast.BitXor: operator.xor,
            ast.USub: operator.neg,
            ast.UAdd: operator.pos,
            ast.Not: operator.not_,
            ast.Invert: operator.invert,
        }
        # Supported types
        self.supported_types = {'int', 'float', 'string', 'char', 'bool', 'byte'}
        # Supported modifiers
        self.supported_modifiers = {'const'}

    def interpret(self, script):
        """
        Interpret and execute the K script.
        """
        lines = script.split('\n')
        output = []
        for line_number, line in enumerate(lines, start=1):
            # Remove inline comments
            line = self.remove_inline_comments(line)
            if not line:
                continue
            if line == '{':
                # Enter a new local scope
                self.local_variables_stack.append({})
                continue
            elif line == '}':
                # Exit the current local scope
                if self.local_variables_stack:
                    self.local_variables_stack.pop()
                else:
                    output.append(f"Line {line_number}: Syntax Error: Unmatched closing brace '}}'.")
                continue
            result = self.execute_line(line, line_number)
            if result is not None:
                # Ensure all output items are strings
                if isinstance(result, list):
                    # If multiple items (like print with multiple arguments), join them
                    result = ' '.join(str(item) for item in result)
                output.append(result)
        return '\n'.join(output)

    def remove_inline_comments(self, line):
        """
        Remove inline comments from a line.
        """
        comment_index = line.find('#')
        if comment_index != -1:
            line = line[:comment_index]
        return line.strip()

    def execute_line(self, line, line_number):
        """
        Execute a single line of K script.
        """
        try:
            if line.startswith("print"):
                # Handle print statement
                return self.handle_print(line[5:].strip(), line_number)
            elif re.match(r'^(private\s+)?(?:(const)\s+)?(\w+\s+)?\w+\s*=\s*.*', line):
                # Handle variable declaration with optional 'private', 'const', and type
                return self.handle_declaration(line, line_number)
            else:
                return f"Line {line_number}: Unknown command: {line}"
        except Exception as e:
            return f"Line {line_number}: Error: {e}"

    def handle_print(self, expression, line_number):
        """
        Handle the print statement.
        """
        if not expression:
            return f"Line {line_number}: Syntax Error: Missing expression in print statement."
        
        # Support for print with parentheses, e.g., print("Hello")
        if expression.startswith('(') and expression.endswith(')'):
            expression = expression[1:-1].strip()
        
        # Support multiple arguments separated by commas, e.g., print("Sum:", x + y)
        expressions = [expr.strip() for expr in self.split_expressions(expression)]
        values = []
        for expr in expressions:
            try:
                # Check if the expression is a variable for type-specific handling
                var_info = self.get_variable_info(expr)
                if var_info:
                    value = self.evaluate_expression(expr, line_number)
                    if var_info['type'] == 'byte':
                        # Convert to binary with leading zeros
                        value = format(var_info['value'], '08b')
                    elif var_info['type'] == 'bool':
                        value = str(value)
                    values.append(value)
                else:
                    # Expression is not a direct variable; evaluate it
                    value = self.evaluate_expression(expr, line_number)
                    # For standalone expressions, handle their types
                    if isinstance(value, bool):
                        value = str(value)
                    values.append(value)
            except Exception as e:
                values.append(str(e))
        return values  # Return as list to join with spaces in interpret()

    def split_expressions(self, expression):
        """
        Split expressions by commas, respecting parentheses and quotes.
        """
        expressions = []
        current_expr = ''
        parentheses = 0
        quotes = False
        quote_char = ''
        for char in expression:
            if char in ('"', "'"):
                if not quotes:
                    quotes = True
                    quote_char = char
                elif quotes and char == quote_char:
                    quotes = False
            elif char == '(' and not quotes:
                parentheses += 1
            elif char == ')' and not quotes:
                parentheses -= 1
            elif char == ',' and not quotes and parentheses == 0:
                expressions.append(current_expr)
                current_expr = ''
                continue
            current_expr += char
        if current_expr:
            expressions.append(current_expr)
        return expressions

    def handle_declaration(self, line, line_number):
        """
        Handle variable declarations with optional 'private', 'const', and type annotations.
        Syntax: [private] [const] [<type>] <varname> = <expression>
        """
        # Regex to parse the declaration
        match = re.match(r'^(private\s+)?(?:(const)\s+)?(?:(\w+)\s+)?(\w+)\s*=\s*(.+)$', line)
        if not match:
            return f"Line {line_number}: Syntax Error: Invalid variable declaration."

        is_private, modifier, var_type, var_name, expr = match.groups()

        # Check if the variable is already declared
        var_info = self.get_variable_info(var_name)
        if var_info:
            # Variable is already declared; handle reassignment
            if modifier:
                return f"Line {line_number}: Syntax Error: Cannot redeclare variable '{var_name}' with modifier '{modifier}'."
            if var_info['const']:
                return f"Line {line_number}: Type Error: Cannot reassign to constant variable '{var_name}'."
            if var_type:
                return f"Line {line_number}: Syntax Error: Cannot change the type of an existing variable '{var_name}'."
            # Reassignment without type
            value = self.evaluate_expression(expr.strip(), line_number)
            # Handle 'byte' type validation
            if var_info['type'] == 'byte':
                if isinstance(value, int):
                    if not (0 <= value <= 255):
                        return f"Line {line_number}: Type Error: 'byte' type must be an integer between 0 and 255."
                else:
                    return f"Line {line_number}: Type Error: 'byte' type must be assigned an integer value."
            # Handle 'bool' type casting
            if var_info['type'] == 'bool':
                if isinstance(value, str):
                    if value.lower() == 'true':
                        value = True
                    elif value.lower() == 'false':
                        value = False
                    else:
                        return f"Line {line_number}: Type Error: Cannot cast string '{value}' to bool."
                elif isinstance(value, bool):
                    pass  # Already a bool
                else:
                    return f"Line {line_number}: Type Error: Cannot cast value '{value}' to bool."
            # Handle 'char' type validation
            if var_info['type'] == 'char':
                if isinstance(value, str):
                    if len(value) != 1:
                        return f"Line {line_number}: Type Error: 'char' type must be a single character."
                else:
                    return f"Line {line_number}: Type Error: Cannot assign non-string value to 'char' type."
            # Assign the new value
            self.assign_variable(var_name, var_info['type'], value, is_private, var_info['const'])
            return None  # Successful reassignment

        # Variable is not declared yet; handle declaration
        # If type is not specified, infer it
        if var_type is None:
            inferred_type, value = self.infer_type(expr.strip(), line_number)
            if inferred_type is None:
                return value  # 'value' contains the error message
            var_type = inferred_type
        else:
            var_type = var_type.strip()
            if var_type not in self.supported_types:
                return f"Line {line_number}: Type Error: Unsupported type '{var_type}'. Supported types are: {', '.join(self.supported_types)}."
            value = self.evaluate_expression(expr.strip(), line_number)
            # Handle 'bool' type casting
            if var_type == 'bool':
                if isinstance(value, str):
                    if value.lower() == 'true':
                        value = True
                    elif value.lower() == 'false':
                        value = False
                    else:
                        return f"Line {line_number}: Type Error: Cannot cast string '{value}' to bool."
                elif isinstance(value, bool):
                    pass  # Already a bool
                else:
                    return f"Line {line_number}: Type Error: Cannot cast value '{value}' to bool."
            # Handle 'char' type validation
            if var_type == 'char':
                if isinstance(value, str):
                    if len(value) != 1:
                        return f"Line {line_number}: Type Error: 'char' type must be a single character."
                else:
                    return f"Line {line_number}: Type Error: Cannot assign non-string value to 'char' type."
            # Handle 'byte' type validation
            if var_type == 'byte':
                if isinstance(value, int):
                    if not (0 <= value <= 255):
                        return f"Line {line_number}: Type Error: 'byte' type must be an integer between 0 and 255."
                else:
                    return f"Line {line_number}: Type Error: 'byte' type must be assigned an integer value."

        # Determine if the variable is constant
        is_const = True if modifier else False

        # Assign the variable
        self.assign_variable(var_name, var_type, value, is_private, is_const)
        return None  # Assignments do not produce output

    def assign_variable(self, var_name, var_type, value, is_private, is_const=False):
        """
        Assign the variable with type, value, and const status.
        """
        var_data = {'type': var_type, 'value': value, 'const': is_const}
        if is_private:
            if not self.local_variables_stack:
                # If private modifier is used outside of a block, treat it as global
                self.global_variables[var_name] = var_data
            else:
                self.local_variables_stack[-1][var_name] = var_data
        else:
            self.global_variables[var_name] = var_data

    def infer_type(self, expr, line_number):
        """
        Infer the type of the expression based on its evaluated value.
        Returns a tuple (type_name, value) or (None, error_message).
        """
        value = self.evaluate_expression(expr, line_number)
        if isinstance(value, int):
            return ('int', value)
        elif isinstance(value, float):
            return ('float', value)
        elif isinstance(value, bool):
            return ('bool', value)
        elif isinstance(value, str):
            if len(value) == 1:
                return ('char', value)
            else:
                return ('string', value)
        else:
            return (None, f"Line {line_number}: Type Inference Error: Unsupported value type '{type(value).__name__}'.")

    def evaluate_expression(self, expr, line_number):
        """
        Safely evaluate an arithmetic expression using AST.
        Supports the 'type()' and '!' (invert) operators.
        """
        # Replace '!' with 'invert(' only when it's a standalone operator (not part of '!=')
        expr = self.replace_invert_operator(expr)
        try:
            node = ast.parse(expr, mode='eval').body
            return self._evaluate_ast(node, line_number)
        except SyntaxError:
            raise ValueError(f"Line {line_number}: Evaluation Error: invalid syntax")
        except Exception as e:
            raise ValueError(f"Line {line_number}: Evaluation Error: {e}")

    def replace_invert_operator(self, expr):
        """
        Replace '!' with 'invert(' while ensuring '!=' is not altered.
        """
        # Replace '!' not followed by '=' with 'invert('
        expr = re.sub(r'!(?!\=)', 'invert(', expr)
        # Count the number of 'invert(' replaced to add closing parentheses
        num_inverts = expr.count('invert(')
        expr += ')' * num_inverts  # Add closing parentheses for each 'invert('
        return expr

    def _evaluate_ast(self, node, line_number):
        """
        Recursively evaluate an AST node.
        """
        if isinstance(node, ast.Num):  # <number>
            return node.n
        elif isinstance(node, ast.Str):  # <string>
            return node.s
        elif isinstance(node, ast.Constant):  # Python 3.8+
            return node.value
        elif isinstance(node, ast.BinOp):  # <left> <operator> <right>
            op_type = type(node.op)
            if op_type in self.operators:
                left = self._evaluate_ast(node.left, line_number)
                right = self._evaluate_ast(node.right, line_number)
                return self.operators[op_type](left, right)
            else:
                raise ValueError(f"Unsupported operator: {op_type.__name__}")
        elif isinstance(node, ast.UnaryOp):  # <operator> <operand> e.g., -1, invert(x)
            op_type = type(node.op)
            if op_type in self.operators:
                operand = self._evaluate_ast(node.operand, line_number)
                return self.operators[op_type](operand)
            else:
                raise ValueError(f"Unsupported unary operator: {op_type.__name__}")
        elif isinstance(node, ast.Name):
            id = node.id.lower()
            if id == 'true':
                return True
            elif id == 'false':
                return False
            var_info = self.get_variable_info(id)
            if var_info:
                return var_info['value']
            else:
                raise NameError(f"Undefined variable: {id}")
        elif isinstance(node, ast.Call):
            # Handle built-in functions
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
                args = [self._evaluate_ast(arg, line_number) for arg in node.args]
                if func_name == 'type':
                    return self.handle_type_function(args, line_number)
                elif func_name == 'invert':
                    return self.handle_invert_function(args, line_number)
                else:
                    raise ValueError(f"Unsupported function: {func_name}")
            else:
                raise ValueError("Unsupported function call.")
        else:
            raise TypeError(f"Unsupported expression: {type(node).__name__}")

    def handle_type_function(self, args, line_number):
        """
        Handle the built-in type() function.
        Usage: type(variable)
        """
        if len(args) != 1:
            raise ValueError("type() function expects exactly one argument.")
        value = args[0]
        if isinstance(value, bool):
            return 'bool'
        elif isinstance(value, int):
            return 'int'
        elif isinstance(value, float):
            return 'float'
        elif isinstance(value, str):
            if len(value) == 1:
                return 'char'
            else:
                return 'string'
        else:
            return type(value).__name__

    def handle_invert_function(self, args, line_number):
        """
        Handle the invert() function.
        Usage: invert(variable)
        """
        if len(args) != 1:
            raise ValueError("invert() function expects exactly one argument.")
        x = args[0]
        if isinstance(x, bool):
            return not x
        elif isinstance(x, (int, float)):
            return -x
        elif isinstance(x, str) and len(x) == 1:
            # For char, invert the ASCII value and wrap around
            return chr((-ord(x)) & 0xFF)
        else:
            raise TypeError(f"Line {line_number}: Type Error: Cannot invert type '{type(x).__name__}'.")

    def get_variable_info(self, var_name):
        """
        Retrieve the variable's type, value, and const status, checking local scopes first.
        """
        # Check local scopes from top to bottom
        for local_vars in reversed(self.local_variables_stack):
            if var_name in local_vars:
                return local_vars[var_name]
        # Check global variables
        return self.global_variables.get(var_name, None)
