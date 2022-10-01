# Phase 3

from re import T
from typing import Any, Type
import psycopg2

from definitions import *

# Useless, but for reference purposes.
class QueryableOperations:
    Range = "-"
    Equal = None
    GreaterThan = ">"
    LessThan = "<"
    Contains = "{"
    ContainsStrings = []



class Queryable:
    def __init__(self, name: str, kind: type, operations: list, array: bool):
        self.name = name
        self.kind = kind
        self.operations = operations
        self.array = array

    def get_operation(self, query_string) -> str:
        "Get the operation from a query string that is not an array type."

        operation = query_string[0]

        # Equality operation
        if (operation not in ["-", ">", "<", "{"]):
            operation = None

        return operation


    def generate_query(self, query_string) -> str:
        operation: str = self.get_operation(query_string)

        if (operation == QueryableOperations.Contains):
            return f"{self.name} LIKE %s"

        if (operation == QueryableOperations.Equal):
            return f"{self.name} = %s"

        if (operation == QueryableOperations.GreaterThan):
            return f"{self.name} > %s"

        if (operation == QueryableOperations.LessThan):
            return f"{self.name} < %s"

    def generate_query_array(self, table: str, on: str, query: list) -> str:
        if (query[0] == "OR"):
            fields = "%s," * len(query)

            # Get rid of ending ,
            fields = fields[-1:]


            return f"SELECT {on} FROM {table} WHERE {self.name} in ({fields})"

        if (query[0] == "AND"):
            result = "("

            for q in query:
                result += f"SELECT {on} FROM {table} WHERE {self.name} = %s INTERSECT"

            # Get rid of the last 'INTERSECT'
            result = result[-len(" INTERSECT"):]
            result += ")"

            return result

        

    async def validate_query(self, connection, query_string) -> bool:
        "Validate a query string based off of the settings of this Queryable object."

        # Invalid type all together
        if (isinstance(query_string, dict)):
            await connection.code(QueryableCodes.Errors.Type)
            return False

        # If this is not an array type, but the query contained an array.
        if (not self.array and isinstance(query_string, list)):
            await connection.code(QueryableCodes.Errors.Array)
            return False

        # The only operation supported on array queryable types is []
        if (self.array and not isinstance(query_string, list)):
            await connection.code(QueryableCodes.Errors.Type)
            return False

        # If dealing with a non-array type.
        if (not isinstance(query_string, list)):
            operation = self.get_operation(query_string)

            #if (operation in [">", "<"] and not isinstance(self.kind, int)):
            #    await connection.code

            # A non supported operation
            if (operation not in self.operations):
                await connection.code(QueryableCodes.Errors.Misuse, {
                    "field": self.name,
                    "operation": operation
                })
                
                return False


class QueryableQuery:
    def __init__(self, query: Any, queryable: Queryable):
        self.query = query
        self.queryable = queryable

def generate_query(cursor: psycopg2.cursor, table: str, connection, queryables: list) -> list:
    result = f"SELECT * FROM {table} WHERE "

    for queryable in queryables:
        queryable: QueryableQuery = queryable

        # Validate the query given.
        if (not queryable.queryable.validate_query(connection, queryable.query)):
            return None

        result += None

        
