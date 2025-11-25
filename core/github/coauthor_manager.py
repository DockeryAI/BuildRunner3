"""Co-Author Manager"""


class CoAuthorManager:
    def add_coauthor(self, name: str, email: str) -> str:
        """Add co-author line"""
        return f"Co-Authored-By: {name} <{email}>"
