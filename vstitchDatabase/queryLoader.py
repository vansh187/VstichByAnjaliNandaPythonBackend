import os

import yaml


class QueryLoader:
    """Loads a named SQL query from a YAML file inside the sqlQueries package."""

    def __init__(self, yaml_file_name):
        self.yaml_file_name = yaml_file_name
        self.yaml_file_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "sqlQueries",
            yaml_file_name,
        )
        self.queries = self._read_queries_from_file()

    def _read_queries_from_file(self):
        if not os.path.isfile(self.yaml_file_path):
            raise FileNotFoundError(f"SQL query file not found: {self.yaml_file_path}")
        with open(self.yaml_file_path, "r", encoding="utf-8") as yaml_file:
            loaded_queries = yaml.safe_load(yaml_file)
        if not loaded_queries:
            raise ValueError(f"No queries were found in {self.yaml_file_path}")
        return loaded_queries

    def get_query(self, query_key):
        query_text = self.queries.get(query_key)
        if not query_text:
            raise KeyError(f"Query '{query_key}' was not found in {self.yaml_file_path}")
        return query_text
