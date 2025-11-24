"""Commit Builder"""
class CommitBuilder:
    def build_commit_message(self, type: str, message: str, scope: Optional[str] = None) -> str:
        if scope:
            return f"{type}({scope}): {message}"
        return f"{type}: {message}"
