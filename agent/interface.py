from abc import ABC, abstractmethod

class ILLMAgent(ABC):

    @abstractmethod
    def ask(self, user_query: str) -> dict:
        """
        Process a user analytics question.

        Returns a structured response containing:
        - answer
        - tool information
        - chart specification
        """
        pass