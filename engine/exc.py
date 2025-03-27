class ScrapingError(Exception):
    # Raised when an error occurs whilst scraping a card
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class LLMError(Exception):
    # Raised when an error occurs whilst interacting with the LLM API
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)
